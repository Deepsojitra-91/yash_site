"""
Image handling routes for profile pictures and product images
Saves images locally and serves them via Flask routes
"""

from flask import Blueprint, request, jsonify, send_from_directory
import os
import base64
from werkzeug.utils import secure_filename
from PIL import Image
import io

image_bp = Blueprint('image', __name__)


# Define base paths
PHOTOS_DIR = os.path.join(os.getcwd(), 'photos')
PROFILE_PIC_DIR = os.path.join(PHOTOS_DIR, 'profile_pic')
PRODUCTS_DIR = os.path.join(PHOTOS_DIR, 'products')
ADVERTISEMENTS_DIR = os.path.join(PHOTOS_DIR, 'advertisements')


# Ensure directories exist
os.makedirs(PROFILE_PIC_DIR, exist_ok=True)
os.makedirs(PRODUCTS_DIR, exist_ok=True)
os.makedirs(ADVERTISEMENTS_DIR, exist_ok=True)

# Allowed extensions
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def save_base64_image(base64_string, save_path, max_size=(800, 800)):
    """
    Convert base64 to image and save locally
    
    Args:
        base64_string: Base64 encoded image string
        save_path: Full path where image should be saved
        max_size: Maximum dimensions (width, height)
    
    Returns:
        True if successful, False otherwise
    """
    try:
        # Remove data:image prefix if present
        if ',' in base64_string:
            base64_string = base64_string.split(',')[1]
        
        # Decode base64
        image_data = base64.b64decode(base64_string)
        
        # Open image with PIL
        image = Image.open(io.BytesIO(image_data))
        
        # Convert RGBA to RGB if needed
        if image.mode == 'RGBA':
            background = Image.new('RGB', image.size, (255, 255, 255))
            background.paste(image, mask=image.split()[3])
            image = background
        
        # Resize if needed
        image.thumbnail(max_size, Image.Resampling.LANCZOS)
        
        # Save as PNG
        image.save(save_path, 'PNG', optimize=True, quality=85)
        
        return True
        
    except Exception as e:
        print(f"Error saving image: {e}")
        return False


def save_profile_picture(user_id, base64_image):
    """
    Save user profile picture using MongoDB ObjectId as filename
    
    Args:
        user_id: MongoDB ObjectId (converted to string) - UNIQUE identifier
        base64_image: Base64 encoded image
    
    Returns:
        Relative path to saved image or None if failed
    """
    if not base64_image or not user_id:
        return None
    
    # Create filename: user_id.png (e.g., 507f1f77bcf86cd799439011.png)
    filename = f"{user_id}.png"
    save_path = os.path.join(PROFILE_PIC_DIR, filename)
    
    # Delete old image if exists (handles image updates)
    if os.path.exists(save_path):
        try:
            os.remove(save_path)
            print(f"♻️ Replaced old profile picture: {filename}")
        except Exception as e:
            print(f"Warning: Could not delete old image: {e}")
    
    # Save new image
    if save_base64_image(base64_image, save_path, max_size=(400, 400)):
        print(f"✅ Profile picture saved: {filename}")
        return f"profile_pic/{filename}"
    
    return None


def save_product_image(product_id, base64_image):
    """
    Save product image
    
    Args:
        product_id: Product ID or unique identifier
        base64_image: Base64 encoded image
    
    Returns:
        Relative path to saved image or None if failed
    """
    if not base64_image or not product_id:
        return None
    
    # Create filename: product_id.png
    filename = f"{product_id}.png"
    save_path = os.path.join(PRODUCTS_DIR, filename)
    
    # Save image
    if save_base64_image(base64_image, save_path, max_size=(800, 800)):
        return f"products/{filename}"
    
    return None


def delete_profile_picture(user_id):
    """Delete profile picture for given user ID"""
    try:
        filepath = os.path.join(PROFILE_PIC_DIR, f"{user_id}.png")
        if os.path.exists(filepath):
            os.remove(filepath)
            print(f"🗑️ Deleted profile picture: {user_id}.png")
            return True
    except Exception as e:
        print(f"Error deleting profile picture: {e}")
    return False


def delete_product_image(product_id):
    """Delete product image for given product ID"""
    try:
        filepath = os.path.join(PRODUCTS_DIR, f"{product_id}.png")
        if os.path.exists(filepath):
            os.remove(filepath)
            return True
    except Exception as e:
        print(f"Error deleting product image: {e}")
    return False


# ============= ROUTES FOR SERVING IMAGES =============

@image_bp.route('/photos/profile_pic/<filename>')
def serve_profile_pic(filename):
    """Serve profile picture"""
    try:
        return send_from_directory(PROFILE_PIC_DIR, filename)
    except Exception as e:
        print(f"Error serving profile pic: {e}")
        return jsonify({"detail": "Image not found"}), 404


@image_bp.route('/photos/products/<filename>')
def serve_product_image(filename):
    """Serve product image"""
    try:
        return send_from_directory(PRODUCTS_DIR, filename)
    except Exception as e:
        print(f"Error serving product image: {e}")
        return jsonify({"detail": "Image not found"}), 404


@image_bp.route('/api/image/profile-exists/<user_id>')
def check_profile_exists(user_id):
    """Check if profile picture exists for user ID"""
    filepath = os.path.join(PROFILE_PIC_DIR, f"{user_id}.png")
    exists = os.path.exists(filepath)
    return jsonify({
        "exists": exists,
        "path": f"/photos/profile_pic/{user_id}.png" if exists else None
    })


@image_bp.route('/api/image/product-exists/<product_id>')
def check_product_exists(product_id):
    """Check if product image exists"""
    filepath = os.path.join(PRODUCTS_DIR, f"{product_id}.png")
    exists = os.path.exists(filepath)
    return jsonify({
        "exists": exists,
        "path": f"/photos/products/{product_id}.png" if exists else None
    })
    
    
def save_advertisement_image(ad_id, base64_image):
    """Save advertisement image"""
    if not base64_image or not ad_id:
        return None
    
    # Create filename: ad_id.png
    filename = f"{ad_id}.png"
    save_path = os.path.join(ADVERTISEMENTS_DIR, filename)
    
    # Save image
    if save_base64_image(base64_image, save_path, max_size=(1200, 800)):
        return f"advertisements/{filename}"
    
    return None


def delete_advertisement_image(ad_id):
    """Delete advertisement image for given ad ID"""
    try:
        filepath = os.path.join(ADVERTISEMENTS_DIR, f"{ad_id}.png")
        if os.path.exists(filepath):
            os.remove(filepath)
            return True
    except Exception as e:
        print(f"Error deleting advertisement image: {e}")
    return False


@image_bp.route('/photos/advertisements/<filename>')
def serve_advertisement_image(filename):
    """Serve advertisement image"""
    try:
        return send_from_directory(ADVERTISEMENTS_DIR, filename)
    except Exception as e:
        print(f"Error serving advertisement image: {e}")
        return jsonify({"detail": "Image not found"}), 404