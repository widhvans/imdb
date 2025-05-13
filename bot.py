import telegram
from telegram.ext import Application, CommandHandler, MessageHandler, filters
import aiohttp
import config
import logging
import urllib.parse

# Set up logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

async def start(update, context):
    await update.message.reply_text('Hi! Send me a movie name, and I’ll fetch its details. Data from TMDb.')

async def search_movie(update, context):
    movie_name = urllib.parse.quote(update.message.text)
    api_key = config.TMDB_API_KEY
    search_url = f'https://api.themoviedb.org/3/search/movie?api_key={api_key}&query={movie_name}'
    
    async with aiohttp.ClientSession() as session:
        # Fetch movie data
        async with session.get(search_url) as response:
            data = await response.json()

            if data['results']:
                movie = data['results'][0]
                title = movie['title']
                year = movie['release_date'][:4] if movie['release_date'] else 'N/A'
                rating = movie['vote_average'] if movie['vote_average'] else 'N/A'
                overview = movie['overview'] if movie['overview'] else 'No plot available'
                poster_path = movie['poster_path']

                # Fetch configuration for poster base URL
                config_url = f'https://api.themoviedb.org/3/configuration?api_key={api_key}'
                async with session.get(config_url) as config_response:
                    config_data = await config_response.json()
                    base_url = config_data['images']['secure_base_url']
                    poster_size = 'w500'

                message = f"**{title} ({year})**\nTMDb Rating: {rating}/10\nPlot: {overview}\n\nData from themoviedb.org"
                if poster_path and config.USE_POSTERS:
                    poster_url = f"{base_url}{poster_size}{poster_path}"
                    await update.message.reply_photo(photo=poster_url, caption=message, parse_mode='Markdown')
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
