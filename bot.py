import os
import json
import logging
from pathlib import Path

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
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=f"""
Welcome to {BLOG_NAME}. I can help you search for
posts and read them right here in Telegram, as well as unlock
premium posts.

Send /notify to receive new article notifications.

Send /help for detailed instructions.""",
    )


async def help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="""
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
    query = QueryParser("content", index.schema).parse(" ".join(context.args))
    response = []

    with index.searcher() as s:
        results = s.search(query, limit=10)

        for r in results:
            response.append(f"**[{r['title']}]({r['path']}):** {r['subtitle']}")

    await context.bot.send_message(
        update.effective_chat.id,
        text="\n\n".join(response),
        parse_mode="markdown",
        disable_web_page_preview=True,
    )


## MAIN


def main():
    application = ApplicationBuilder().token(BOT_TOKEN).concurrent_updates(True).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help))
    application.add_handler(CommandHandler("notify", notify))
    application.add_handler(CommandHandler("mute", mute))
    application.add_handler(CommandHandler("search", search))

    application.run_polling()


if __name__ == "__main__":
    main()
