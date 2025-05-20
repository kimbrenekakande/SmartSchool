import os
from PIL import Image, ImageDraw, ImageFont

def create_favicon():
    # Create a 32x32 image with white background
    img = Image.new('RGBA', (32, 32), (255, 255, 255, 0))
    d = ImageDraw.Draw(img)
    
    # Draw a simple 'S' in the center
    try:
        # Try to use a font if available
        font = ImageFont.truetype("Arial", 24)
    except IOError:
        # Fallback to default font
        font = ImageFont.load_default()
    
    d.text((8, 4), "SS", font=font, fill=(79, 70, 229))  # indigo-600
    
    # Create static/img directory if it doesn't exist
    os.makedirs('static/img', exist_ok=True)
    
    # Save as favicon.ico
    img.save('static/img/favicon.ico', format='ICO', sizes=[(32, 32)])
    print("Favicon created successfully at static/img/favicon.ico")

if __name__ == "__main__":
    create_favicon()
