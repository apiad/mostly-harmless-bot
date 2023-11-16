# Mostly Harmless Bot

> A Telegram bot to interact with my Substack blog.

### [🤖 Check it out](https://t.me/mostly_harmless_ideas_bot)

---

## Usage

You can this for yourself, but beware there are no guarantees that anything works at all.
Here's how.

- First, create a Telegram bot with [BotFather](https://t.me/BotFather).
- Activate payments (choose your favorite provider).
- Note down the bot TOKEN and the payment TOKEN.

Now clone the project, and create a `.env` file with the following structure:

```bash
# The TOKEN you got from BotFather
BOT_TOKEN=123123213121331
# The payment API TOKEN you fot from BotFather
PAYMENT_TOKEN=12313123131312312
# Your Telegram ID (it's a number, not a username)
ADMIN_ID=1234567
# Information about your blog
BLOG_NAME=Mostly Harmless Ideas
BLOG_FEED=https://blog.apiad.net/feed
BLOG_PATH_PREFIX=https://blog.apiad.net/p/
```

Next, download an archive dump of your files from Substack, and unzip it in the `data` folder. Thus, you get the following:

```bash
data/
  .gitignore
  posts.csv
  posts/
    ... bunch of HTMLs and CSVs
```

Run the indexer process:

```bash
$ python3 indexer.py 600
```

This will first load all your archived posts and then download your feed, pooling every 600 seconds (or whatever interval you want). Thus, you will never again need to dump the archives.

> NOTE: The reason we need the archive dump is because the feed only provides the latest 20 posts. If your blog has less than 20 posts, you can skip that part.

Leave the indexer running, and in a different terminal run the bot script:

```
$ python3 bot.py
```

If everything looks fine in the Terminal, go to your bot in Telegram and hit START. Send `/help` to check your blog's name is rendered correctly, and see the command list. Send `/latest` to check the list of posts is up to date.

### Admin commands

There are a couple unlisted admin commands that only the user with ID equal to `ADMIN_ID` can use.

- `/lock <public_url> <private_url> <price>` will add a new article to the list of premium articles.

  The `public_url` is the Substack URL that everyone can read, i.e., the one where your free subscribers only see a preview.

  The `private_url` is a private draft link (get it from the post settings page) that bypases all subscription constraints.

  The `price` is a number in USD cents, e.g., 200 for $2.

- `/config` will send you the `config.json` file where you can see all the active users of the bot, and the locked articles.

- `/broadcast` lets you send messages to all or some users. To use it, first write whatever you want to send as a regular message to the bot. Then, reply to that message and type `/broadcast`.

    By default this will notify those users who have `/notify` turned on. You can add `all` to notify everyone who's ever interacted with the bot, or specific user IDs to notify only those users.

## License

All code is MIT. Use it at your own risk! :)