import telegram
from telegram.ext import Application, CommandHandler, MessageHandler, filters
import aiohttp
import config
import logging
import urllib.parse
import asyncio

# Set up logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

async def start(update, context):
    await update.message.reply_text('Send a movie name, get a copyright-free, poster-like fan art or scene image from Pixabay (if available) and details. Data from TMDb.')

async def check_rate_limit(response):
    remaining = int(response.headers.get('X-RateLimit-Remaining', 100))
    if remaining < 10:
        reset_time = int(response.headers.get('X-RateLimit-Reset', 60))
        logger.warning(f"Pixabay rate limit low: {remaining} requests left. Pausing for {reset_time} seconds.")
        await asyncio.sleep(reset_time)
    return remaining > 0

async def fetch_pixabay_image(movie_name, pixabay_key):
    url = f'https://pixabay.com/api/?key={pixabay_key}&q={urllib.parse.quote(movie_name + " movie fanart scene -poster")}&image_type=photo,illustration&category=art&safesearch=true&per_page=10&order=popular'
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200 and await check_rate_limit(response):
                data = await response.json()
                if data['hits']:
                    # Pick the most relevant image (highest views)
                    best_hit = max(data['hits'], key=lambda x: x['views'])
                    return best_hit['largeImageURL']
            elif response.status == 429:
                logger.error("Pixabay rate limit exceeded (HTTP 429).")
                return None
    return None

async def search_movie(update, context):
    movie_name = update.message.text
    encoded_movie_name = urllib.parse.quote(movie_name)
    api_key = config.TMDB_API_KEY
    search_url = f'https://api.themoviedb.org/3/search/movie?api_key={api_key}&query={encoded_movie_name}'
    
    async with aiohttp.ClientSession() as session:
        # Fetch movie data
        async with session.get(search_url) as response:
            if response.status != 200:
                await update.message.reply_text('TMDb API error. Try again later.')
                return
            data = await response.json()

            if data['results']:
                movie = data['results'][0]
                title = movie['title']
                year = movie['release_date'][:4] if movie['release_date'] else 'N/A'
                rating = movie['vote_average'] if movie['vote_average'] else 'N/A'
                overview = movie['overview'] if movie['overview'] else 'No plot available'

                # Fetch Pixabay image
                image_url = await fetch_pixabay_image(title, config.PIXABAY_API_KEY)

                message = f"**{title} ({year})**\nTMDb Rating: {rating}/10\nPlot: {overview}\n\nData from themoviedb.org"

                if image_url:
                    await update.message.reply_photo(photo=image_url, caption=f"{message}\n\nImage from Pixabay", parse_mode='Markdown')
                else:
                    await update.message.reply_text(f"{message}\n\nNo copyright-free fan art or scene image found on Pixabay. Try another movie name.", parse_mode='Markdown')
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
