import telegram
from telegram.ext import Application, CommandHandler, MessageHandler, filters
import aiohttp
import config
import logging

# Set up logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

async def start(update, context):
    await update.message.reply_text('Hi! Send me a movie name, and I’ll fetch its poster and IMDb details.')

async def search_movie(update, context):
    movie_name = update.message.text
    api_key = config.OMDB_API_KEY
    url = f'http://www.omdbapi.com/?t={movie_name}&apikey={api_key}'

    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            data = await response.json()

            if data['Response'] == 'True':
                title = data['Title']
                year = data['Year']
                imdb_rating = data['imdbRating']
                plot = data['Plot']
                poster = data['Poster']

                message = f"**{title} ({year})**\nIMDb Rating: {imdb_rating}\nPlot: {plot}"
                if poster != 'N/A':
                    await update.message.reply_photo(photo=poster, caption=message, parse_mode='Markdown')
                else:
                    await update.message.reply_text(message, parse_mode='Markdown')
            else:
                await update.message.reply_text('Movie not found. Please check the name and try again.')

async def error_handler(update, context):
    logger.error(f'Update {update} caused error {context.error}')
    await update.message.reply_text('Something went wrong. Please try again.')

def main():
    app = Application.builder().token(config.TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler('start', start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, search_movie))
    app.add_error_handler(error_handler)

    app.run_polling()

if __name__ == '__main__':
    main()
