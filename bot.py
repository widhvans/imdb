import telegram
from telegram.ext import Application, CommandHandler, MessageHandler, filters
import aiohttp
import config
import logging
import urllib.parse
from PIL import Image, ImageDraw, ImageFont
import io
import random

# Set up logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

async def start(update, context):
    await update.message.reply_text('Hi! Send me a movie name, and I’ll fetch its details with a custom poster. Data from TMDb.')

async def create_custom_poster(title, year):
    # Create a simple 300x450 image with random background color
    bg_color = random.choice([(100, 150, 200), (200, 100, 150), (150, 200, 100)])
    img = Image.new('RGB', (300, 450), bg_color)
    draw = ImageDraw.Draw(img)

    # Default font (Pillow uses a basic font if none is specified)
    try:
        font = ImageFont.truetype("arial.ttf", 24)  # Use Arial if available
    except:
        font = ImageFont.load_default()

    # Add movie title and year
    text = f"{title}\n({year})"
    draw.text((20, 200), text, fill=(255, 255, 255), font=font)

    # Save image to bytes
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format='PNG')
    img_byte_arr.seek(0)
    return img_byte_arr

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

                # Generate custom poster
                poster_file = await create_custom_poster(title, year)

                # Send response
                message = f"**{title} ({year})**\nTMDb Rating: {rating}/10\nPlot: {overview}\n\nData from themoviedb.org"
                await update.message.reply_photo(photo=poster_file, caption=message, parse_mode='Markdown')
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
