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
    await update.message.reply_text('Send a movie name, get a copyright-free, poster-like fan art or scene image from Unsplash or Pexels (if available) and details. Data from TMDb.')

async def check_unsplash_rate_limit(response):
    remaining = int(response.headers.get('X-Ratelimit-Remaining', 50))
    if remaining < 5:
        logger.warning(f"Unsplash rate limit low: {remaining} requests left. Pausing for 3600 seconds.")
        await asyncio.sleep(3600)  # Wait 1 hour
    return remaining > 0

async def check_pexels_rate_limit(response):
    remaining = int(response.headers.get('X-Ratelimit-Remaining', 200))
    if remaining < 10:
        logger.warning(f"Pexels rate limit low: {remaining} requests left. Pausing for 3600 seconds.")
        await asyncio.sleep(3600)  # Wait 1 hour
    return remaining > 0

async def fetch_unsplash_image(movie_name, unsplash_key):
    queries = [
        f"{movie_name} movie fanart -poster",
        f"{movie_name} cinematic -poster",
        f"{movie_name} movie scene -poster"
    ]
    headers = {"Authorization": f"Client-ID {unsplash_key}"}
    async with aiohttp.ClientSession() as session:
        for query in queries:
            url = f'https://api.unsplash.com/search/photos?query={urllib.parse.quote(query)}&orientation=portrait&per_page=30&order_by=relevant&content_filter=low'
            async with session.get(url, headers=headers) as response:
                if response.status == 200 and await check_unsplash_rate_limit(response):
                    data = await response.json()
                    logger.info(f"Unsplash query '{query}': {len(data.get('results', []))} hits")
                    if data['results']:
                        best_hit = max(data['results'], key=lambda x: x['likes'])
                        return best_hit['urls']['regular'], 'Unsplash'
                elif response.status == 429:
                    logger.error(f"Unsplash rate limit exceeded for query '{query}' (HTTP 429).")
                    return None, None
                else:
                    logger.error(f"Unsplash query '{query}' failed with status {response.status}")
    return None, None

async def fetch_pexels_image(movie_name, pexels_key):
    queries = [
        f"{movie_name} movie fanart -poster",
        f"{movie_name} cinematic -poster",
        f"{movie_name} movie scene -poster"
    ]
    headers = {"Authorization": pexels_key}
    async with aiohttp.ClientSession() as session:
        for query in queries:
            url = f'https://api.pexels.com/v1/search?query={urllib.parse.quote(query)}&per_page=30&orientation=portrait'
            async with session.get(url, headers=headers) as response:
                if response.status == 200 and await check_pexels_rate_limit(response):
                    data = await response.json()
                    logger.info(f"Pexels query '{query}': {len(data.get('photos', []))} hits")
                    if data['photos']:
                        best_hit = max(data['photos'], key=lambda x: x['avg_color'] and x['width'] * x['height'])  # Approximate relevance by size
                        return best_hit['src']['large'], 'Pexels'
                elif response.status == 429:
                    logger.error(f"Pexels rate limit exceeded for query '{query}' (HTTP 429).")
                    return None, None
                else:
                    logger.error(f"Pexels query '{query}' failed with status {response.status}")
    return None, None

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

                # Try Unsplash first
                image_url, source = await fetch_unsplash_image(title, config.UNSPLASH_API_KEY)
                # Fall back to Pexels if no Unsplash image
                if not image_url:
                    image_url, source = await fetch_pexels_image(title, config.PEXELS_API_KEY)

                message = f"**{title} ({year})**\nTMDb Rating: {rating}/10\nPlot: {overview}\n\nData from themoviedb.org"

                if image_url:
                    await update.message.reply_photo(photo=image_url, caption=f"{message}\n\nImage from {source}", parse_mode='Markdown')
                else:
                    await update.message.reply_text(f"{message}\n\nNo copyright-free fan art or scene image found for '{title}'. Try popular movies like 'Avengers' or 'Star Wars'.", parse_mode='Markdown')
            else:
                await update.message.reply_text('Movie not found. Please check the name and try again.')

async def error_handler(update, context):
    logger.error(f"Update {update} caused error {context.error}")
    await update.message.reply_text('Something went wrong. Please try again.')

def main():
    try:
        app = Application.builder().token(config.TELEGRAM_TOKEN).build()
    except AttributeError as e:
        logger.error(f"Config error: {e}")
        print("Error: Missing TELEGRAM_TOKEN in config.py")
        return

    app.add_handler(CommandHandler('start', start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, search_movie))
    app.add_error_handler(error_handler)

    app.run_polling()

if __name__ == '__main__':
    main()
