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
    await update.message.reply_text('Send a movie name, get a copyright-free, poster-like scene image (if available) and details. Data from TMDb.')

async def fetch_wikimedia_image(movie_name):
    # Search Wikimedia Commons for movie stills or fan art (not posters)
    url = f'https://commons.wikimedia.org/w/api.php?action=query&list=search&srsearch={urllib.parse.quote(movie_name + " movie still fanart -poster")}&srnamespace=6&format=json'
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            data = await response.json()
            if data['query']['search']:
                file = data['query']['search'][0]['title']
                file_url = f'https://commons.wikimedia.org/w/api.php?action=query&titles={urllib.parse.quote(file)}&prop=imageinfo&iiprop=url&format=json'
                async with session.get(file_url) as file_response:
                    file_data = await file_response.json()
                    pages = file_data['query']['pages']
                    for page in pages.values():
                        if 'imageinfo' in page:
                            return page['imageinfo'][0]['url']
    return None

async def fetch_pixabay_image(movie_name):
    # Search Pixabay for CC0-licensed fan art or movie-inspired images
    pixabay_key = config.PIXABAY_API_KEY  # Optional, Pixabay works without key but limited
    url = f'https://pixabay.com/api/?key={pixabay_key}&q={urllib.parse.quote(movie_name + " movie fanart -poster")}&image_type=photo&category=art'
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            data = await response.json()
            if data['hits']:
                return data['hits'][0]['largeImageURL']
    return None

async def search_movie(update, context):
    movie_name = update.message.text
    encoded_movie_name = urllib.parse.quote(movie_name)
    api_key = config.TMDB_API_KEY
    search_url = f'https://api.themoviedb.org/3/search/movie?api_key={api_key}&query={encoded_movie_name}'
    
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

                # Try Wikimedia for public domain stills or fan art
                image_url = await fetch_wikimedia_image(title)
                if not image_url:
                    # Try Pixabay for CC0 fan art
                    image_url = await fetch_pixabay_image(title)

                message = f"**{title} ({year})**\nTMDb Rating: {rating}/10\nPlot: {overview}\n\nData from themoviedb.org"

                if image_url:
                    await update.message.reply_photo(photo=image_url, caption=message, parse_mode='Markdown')
                else:
                    await update.message.reply_text(f"{message}\n\nNo copyright-free scene or fan art found. Try an older movie (pre-1929) for images.", parse_mode='Markdown')
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
