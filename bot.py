import os
import json
import logging
from pathlib import Path
import random

from dotenv import load_dotenv
from telegram import LabeledPrice, Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    PreCheckoutQueryHandler,
    filters,
)

from whoosh.index import open_dir
from whoosh.qparser import QueryParser
from whoosh.query import Query
from whoosh.searching import Searcher


load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
PAYMENT_TOKEN = os.getenv("PAYMENT_TOKEN")
BLOG_NAME = os.getenv("BLOG_NAME")
BLOG_FEED = os.getenv("BLOG_FEED")
ADMIN_ID = int(os.getenv("ADMIN_ID"))


index = open_dir("data")


logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)


def load_config():
    config_path = Path(__file__).parent / "config.json"

    if not config_path.exists():
        return {}

    with open(config_path) as fp:
        return json.load(fp)


def update_config(**kwargs):
    config = load_config()
    config.update(**kwargs)
    config_path = Path(__file__).parent / "config.json"

    with open(config_path, "w") as fp:
        return json.dump(config, fp, indent=4)


def add_notify(user_id):
    notifications = set(load_config().get("notifications", []))
    notifications.add(user_id)
    update_config(notifications=list(notifications))


def remove_notify(user_id):
    notifications = set(load_config().get("notifications", []))
    notifications.remove(user_id)
    update_config(notifications=list(notifications))


## BOT METHODS


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    _register_user(update)

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=f"""
Welcome to {BLOG_NAME}. I can help you search for
posts and read them right here in Telegram, as well as unlock
premium posts.

Send /help for detailed instructions.""",
    )

    if context.args:
        await context.bot.send_message(update.effective_chat.id, text="Looking for post to unlock.")
        await unlock_post(update, context)


def _register_user(update):
    users = load_config().get('users', [])
    users.append(update.effective_user.id)
    update_config(users = list(set(users)))


async def help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    _register_user(update)

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=f"""
Welcome to {BLOG_NAME}.

I can help you search for posts and read them right here in Telegram, as well as unlock
premium posts.

Send /latest to see the last 10 posts published.

Send /notify to receive a notification here every time a new article is posted (/mute to cancel).

Send /search followed by some text to find for relevant posts related to that text. This is a simple text-based search.

Send /unlock to see a list of premium posts that you can buy individually.
""",
    )


async def notify(update: Update, context: ContextTypes.DEFAULT_TYPE):
    _register_user(update)

    user_id = update.effective_user.id
    add_notify(user_id)
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Notifications are turned on. Send /mute to turn off.",
    )


async def mute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    remove_notify(user_id)
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Notifications are turned off. Send /notify to turn on.",
    )


## SEARCH


async def search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    _register_user(update)

    query = QueryParser("content", index.schema).parse(" ".join(context.args))
    response = []

    with index.searcher() as s:
        results = s.search(query, limit=10)

        for r in results:
            response.append(f"**[{r['title']}]({r['path']}):** {r['subtitle']}")

    if not response:
        await context.bot.send_message(
           update.effective_chat.id,
            text="No relevant articles found.",
        )
        return

    await context.bot.send_message(
        update.effective_chat.id,
        text="\n\n".join(response),
        parse_mode="markdown",
        disable_web_page_preview=True,
    )


async def latest(update: Update, context: ContextTypes.DEFAULT_TYPE):
    _register_user(update)

    response = []

    with open("data/items.json") as fp:
        items = json.load(fp).values()
        items = sorted(items, key=lambda i: i['date'], reverse=True)

        for r in items[:10]:
            response.append(f"**[{r['title']}]({r['path']}):** {r['subtitle']}")

    if not response:
        await context.bot.send_message(
           update.effective_chat.id,
            text="No articles found.",
        )
        return

    await context.bot.send_message(
        update.effective_chat.id,
        text="\n\n".join(response),
        parse_mode="markdown",
        disable_web_page_preview=True,
    )


async def random_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    _register_user(update)

    with open("data/items.json") as fp:
        items = json.load(fp)

    post = items[random.choice(list(items))]

    await context.bot.send_message(
        update.effective_chat.id,
        text=f"**[{post['title']}]({post['path']}):** {post['subtitle']}",
        parse_mode="markdown",
    )


## SUBSCRIPTIONS


async def lock_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    public, secret, price = context.args
    price = int(price)

    config = load_config()
    locked = config.get("locked", {})
    locked[public] = dict(secret=secret, price=price)
    update_config(locked = locked)

    await context.bot.send_message(
        update.effective_chat.id,
        text=f"**{public}** has been locked.",
        parse_mode="markdown",
    )


async def unlock_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    _register_user(update)

    with open("data/items.json") as fp:
        all_items = json.load(fp)

    config = load_config()
    locked = config.get("locked", {})
    locked_items = [path for path in locked if path in all_items]

    if context.args:
        locked_items = [path for path in locked_items if path.endswith(context.args[0])]

    if not locked_items:
        await context.bot.send_message(update.effective_chat.id, text="No matching posts.")
        return

    for path in locked_items:
        title = all_items[path]['title']
        description = all_items[path]['subtitle']
        # select a payload just for you to recognize its the donation from your bot
        payload = path
        # In order to get a provider_token see https://core.telegram.org/bots/payments#getting-a-token
        currency = "USD"
        # price in dollars
        prices = [LabeledPrice(f"Unlock post", locked[path]['price'])]

        # optionally pass need_name=True, need_phone_number=True,
        # need_email=True, need_shipping_address=True, is_flexible=True
        await context.bot.send_invoice(
            update.effective_chat.id,
            title,
            description,
            payload,
            PAYMENT_TOKEN,
            currency,
            prices
        )


# after (optional) shipping, it's the pre-checkout
async def precheckout_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Answers the PreQecheckoutQuery"""
    query = update.pre_checkout_query
    config = load_config()
    locked = config.get("locked", {})

    # check the payload, is this from your bot?
    if not query.invoice_payload in locked:
        # answer False pre_checkout_query
        await query.answer(ok=False, error_message="Something went wrong...")
    else:
        await query.answer(ok=True)


async def successful_payment_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Confirms the successful payment."""
    # do something after successfully receiving payment?
    config = load_config()
    locked = config.get("locked", {})
    path = update.effective_message.successful_payment.invoice_payload
    item = locked[path]

    await update.effective_message.reply_text(f"""
Thank you for your purchase!

You can read the full post [here]({item['secret']}).
""", parse_mode="markdown")


## ADMIN


async def config(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    await context.bot.send_document(update.effective_chat.id, "config.json")


async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    message = update.effective_message.reply_to_message
    config = load_config()

    if context.args:
        if context.args[1] == "all":
            users = config['users']
        else:
            users = [int(u) for u in context.args]
    else:
        users = config['notifications']

    for user in users:
        await message.copy(chat_id=user)


## MAIN


def main():
    application = ApplicationBuilder().token(BOT_TOKEN).concurrent_updates(True).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help))
    application.add_handler(CommandHandler("broadcast", broadcast))
    application.add_handler(CommandHandler("config", config))
    application.add_handler(CommandHandler("notify", notify))
    application.add_handler(CommandHandler("mute", mute))
    application.add_handler(CommandHandler("search", search))
    application.add_handler(CommandHandler("random", random_post))
    application.add_handler(CommandHandler("latest", latest))
    application.add_handler(CommandHandler("lock", lock_post))
    application.add_handler(CommandHandler("unlock", unlock_post))
    application.add_handler(PreCheckoutQueryHandler(precheckout_callback))
    application.add_handler(
        MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment_callback)
    )

    application.run_polling()


if __name__ == "__main__":
    main()
