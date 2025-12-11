from flask import Blueprint, request, jsonify, render_template, session
from bson import ObjectId
from datetime import datetime, timedelta
from extensions import mongo, pwd_context,is_strong_password
import traceback
import os 
from dotenv import load_dotenv
from extensions import admin_login_required
from routes.image_routes import save_product_image, delete_product_image

admin_bp = Blueprint("admin", __name__)

load_dotenv()

ADMIN_USERNAME = os.getenv("ADMIN_USERNAME") 
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")

def get_password_hash(password: str):
    password = str(password)[:72]
    return pwd_context.hash(password)

def now_ist():
    from datetime import timezone
    ist = timezone(timedelta(hours=5, minutes=30))
    return datetime.now(ist).replace(tzinfo=None)

def generate_id_number():
    approved_count = mongo.db.users.count_documents({"is_approved": True})
    id_number = approved_count + 1

    if id_number == 1:
        return "AAVT1"
    elif id_number <= 11:
        return f"BAVT{id_number - 1}"
    elif id_number <= 111:
        return f"CAVT{id_number - 11}"
    elif id_number <= 1111:
        return f"DAVT{id_number - 111}"
    elif id_number <= 11111:
        return f"EAVT{id_number - 1111}"
    elif id_number <= 111111:
        return f"FAVT{id_number - 11111}"
    elif id_number <= 1111111:
        return f"GAVT{id_number - 111111}"
    else:
        return f"HAVT{id_number - 1111111}"


def generate_approval_serial():
    approved_count = mongo.db.users.count_documents({"is_approved": True})
    return approved_count + 1


@admin_bp.route("/admin-login")
def admin_login_page():
    return render_template("admin/admin-login.html")


@admin_bp.route("/admin-dashboard")
@admin_login_required
def admin_dashboard_page():
    return render_template("admin/admin-dashboard.html")


@admin_bp.route("/admin-create-user")
@admin_login_required
def admin_create_user_page():
    return render_template("admin/admin-create-user.html")


@admin_bp.route("/admin-add-product")
@admin_login_required
def admin_add_product_page():
    return render_template("admin/admin-add-product.html")


@admin_bp.route("/admin-products")
@admin_login_required
def admin_products_page():
    return render_template("admin/admin-products.html")


@admin_bp.route("/admin-all-users")
@admin_login_required
def admin_all_users_page():
    return render_template("admin/admin-all-users.html")


@admin_bp.route("/admin-change-level")
def admin_change_level_page():
    return render_template("admin/change-level.html")


@admin_bp.route("/admin-notifications")
@admin_login_required
def admin_notifications_page():
    return render_template("admin/admin-notifications.html")


@admin_bp.route("/api/admin-login", methods=["POST"])
def admin_login():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"detail": "No data provided"}), 400

        username = data.get("username", "").strip()
        password = data.get("password", "").strip()

        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session['admin'] = {
                "username": username,
                "role": "admin"
            }

            return jsonify({
                "message": "Login successful",
                "username": username,
                "role": "admin"
            }), 200
        else:
            return jsonify({"detail": "Invalid username or password"}), 401

    except Exception as e:
        print(f"ERROR in admin_login: {str(e)}")
        traceback.print_exc()
        return jsonify({"detail": "Server error occurred"}), 500


@admin_bp.route("/api/admin/stats", methods=["GET"])
def admin_stats():
    try:
        # Total approved users
        total_users = mongo.db.users.count_documents({
            "is_approved": True,
            "is_rejected": False
        })

        # Total products
        total_products = mongo.db.products.count_documents({})

        # Pending users
        pending_users = mongo.db.users.count_documents({
            "is_approved": False,
            "is_rejected": False
        })

        return jsonify({
            "total_users": total_users,
            "total_products": total_products,
            "pending_users": pending_users
        }), 200

    except Exception as e:
        print("Stats error:", e)
        return jsonify({"detail": "Failed to load statistics"}), 500


@admin_bp.route("/api/admin/all-users", methods=["GET"])
def get_all_users():
    try:
        users = list(mongo.db.users.find().sort("created_at", -1))
        
        for u in users:
            u["_id"] = str(u["_id"])
            u["status"] = (
                "Approved" if u.get("is_approved")
                else "Rejected" if u.get("is_rejected")
                else "Pending"
            )
            u["real_password"] = u.get("plain_password", "-")
            u["approval_serial"] = u.get("approval_serial", "-")
            
            # ============ CHANGED: Convert path to full URL ============
            profile_pic_path = u.get("profile_pic")
            if profile_pic_path:
                u["profile_pic"] = f"/photos/{profile_pic_path}"
            else:
                u["profile_pic"] = ""
            # ===========================================================
        
        return jsonify({"users": users}), 200
    
    except Exception as e:
        print(f"ERROR in get_all_users: {str(e)}")
        return jsonify({"detail": "Server error"}), 500
    

@admin_bp.route("/api/admin/pending-users", methods=["GET"])
def get_pending_users():
    try:
        pending_users = list(
            mongo.db.users.find({"is_approved": False, "is_rejected": False})
            .sort("created_at", -1)
        )

        for user in pending_users:
            user["_id"] = str(user["_id"])
            
            # ============ CHANGED: Convert path to full URL ============
            profile_pic_path = user.get("profile_pic")
            if profile_pic_path:
                user["profile_pic"] = f"/photos/{profile_pic_path}"
            else:
                user["profile_pic"] = ""
            # ===========================================================

        return jsonify({"pending_users": pending_users}), 200

    except Exception as e:
        print(f"ERROR in get_pending_users: {str(e)}")
        traceback.print_exc()
        return jsonify({"detail": f"Error: {str(e)}"}), 500


@admin_bp.route("/api/admin/notifications", methods=["GET"])
def get_notifications():
    try:
        notifications = list(
            mongo.db.notifications.find({"read": False}).sort("created_at", -1)
        )
        for notif in notifications:
            notif["_id"] = str(notif["_id"])

        return jsonify({"notifications": notifications}), 200

    except Exception as e:
        print(f"ERROR in get_notifications: {str(e)}")
        traceback.print_exc()
        return jsonify({"detail": f"Error: {str(e)}"}), 500


@admin_bp.route("/api/admin/user-by-id", methods=["GET"])
def admin_get_user_by_id():
    id_number = request.args.get("id_number", "").strip()

    if not id_number:
        return jsonify({"detail": "ID number required"}), 400

    user = mongo.db.users.find_one({"id_number": id_number})

    if not user:
        return jsonify({"detail": "User not found"}), 404

    return jsonify({
        "_id": str(user["_id"]),
        "current_level": user.get("current_level", "-"),
        "upcoming_level": user.get("upcoming_level", "Bronze")
    }), 200


@admin_bp.route("/api/admin/update-user-level", methods=["POST"])
def update_user_level():
    try:
        data = request.get_json()
        id_number = data.get("id_number")
        current_level = data.get("current_level")
        upcoming_level = data.get("upcoming_level")

        user = mongo.db.users.find_one({"id_number": id_number})

        if not user:
            return jsonify({"detail": "User not found"}), 404

        mongo.db.users.update_one(
            {"id_number": id_number},
            {
                "$set": {
                    "current_level": current_level,
                    "upcoming_level": upcoming_level,
                    "updated_at": now_ist()
                }
            }
        )

        return jsonify({"message": "Level updated successfully"}), 200

    except Exception as e:
        print("Level update error:", e)
        return jsonify({"detail": "Server error"}), 500


@admin_bp.route("/api/admin/users", methods=["GET"])
def paginated_users():
    try:
        status = request.args.get("status", "All")
        mobile_sort = request.args.get("mobile_sort", "none")
        search = request.args.get("search", "").strip()
        page = int(request.args.get("page", 1))
        limit = int(request.args.get("limit", 10))
        skip = (page - 1) * limit

        query = {}

        if status == "Approved":
            query = {"is_approved": True, "is_rejected": False}
        elif status == "Rejected":
            query = {"is_rejected": True}
        elif status == "Pending":
            query = {"is_approved": False, "is_rejected": False}

        if search:
            query["$or"] = [
                {"full_name": {"$regex": search, "$options": "i"}},
                {"mobile": {"$regex": search, "$options": "i"}},
                {"id_number": {"$regex": search, "$options": "i"}},
            ]

        if mobile_sort in ["high", "low"]:

            pipeline = [
                {"$match": query},
                {"$group": {
                    "_id": "$mobile",
                    "count": {"$sum": 1},
                    "users": {"$push": "$$ROOT"}
                }},
                {"$sort": {"count": -1 if mobile_sort == "high" else 1}},
                {"$project": {
                    "users": {
                        "$slice": ["$users", limit]   # still paginate
                    }
                }},
                {"$skip": skip},
                {"$limit": limit}
            ]

            groups = list(mongo.db.users.aggregate(pipeline))

            # Flatten users
            result = []
            for g in groups:
                for u in g["users"]:
                    u["_id"] = str(u["_id"])
                    u["status"] = (
                        "Approved" if u.get("is_approved")
                        else "Rejected" if u.get("is_rejected")
                        else "Pending"
                    )
                    u["real_password"] = u.get("plain_password", "-")
                    u["approval_serial"] = u.get("approval_serial", "-")
                    profile_pic_path = u.get("profile_pic")
                    u["profile_pic"] = f"/photos/{profile_pic_path}" if profile_pic_path else ""

                    result.append(u)

            total = mongo.db.users.count_documents(query)

            return jsonify({
                "users": result,
                "page": page,
                "limit": limit,
                "total_pages": (total + limit - 1) // limit
            }), 200

        total = mongo.db.users.count_documents(query)

        users = (
            mongo.db.users.find(query)
            .sort("_id", -1)
            .skip(skip)
            .limit(limit)
        )

        result = []
        for u in users:
            u["_id"] = str(u["_id"])
            u["status"] = (
                "Approved" if u.get("is_approved")
                else "Rejected" if u.get("is_rejected")
                else "Pending"
            )
            u["real_password"] = u.get("plain_password", "-")
            u["approval_serial"] = u.get("approval_serial", "-")
            profile_pic_path = u.get("profile_pic")
            u["profile_pic"] = f"/photos/{profile_pic_path}" if profile_pic_path else ""

            result.append(u)

        return jsonify({
            "users": result,
            "page": page,
            "limit": limit,
            "total_pages": (total + limit - 1) // limit
        }), 200

    except Exception as e:
        print("ERROR:", e)
        return jsonify({"detail": "Server error"}), 500




@admin_bp.route("/api/admin/users/by-mobile-frequency", methods=["GET"])
def users_by_mobile_frequency():
    try:
        order = request.args.get("order", "high-low")

        freq = mongo.db.users.aggregate([
            {"$group": {"_id": "$mobile", "count": {"$sum": 1}}}
        ])

        freq_map = {item["_id"]: item["count"] for item in freq}

        users = list(mongo.db.users.find().sort("created_at", -1))

        for u in users:
            u["_id"] = str(u["_id"])
            u["frequency"] = freq_map.get(u.get("mobile"), 1)
            u["status"] = (
                "Approved" if u.get("is_approved")
                else "Rejected" if u.get("is_rejected")
                else "Pending"
            )
            u["real_password"] = u.get("plain_password", "-")
            profile_pic_path = u.get("profile_pic")
            u["profile_pic"] = f"/photos/{profile_pic_path}" if profile_pic_path else ""


        users.sort(key=lambda x: x["frequency"], reverse=(order == "high-low"))

        return jsonify({"users": users}), 200

    except Exception as e:
        print("ERROR:", e)
        return jsonify({"detail": "Error sorting data"}), 500


@admin_bp.route("/api/admin/user-details/<user_id>", methods=["GET"])
def get_user_details(user_id):
    try:
        user = mongo.db.users.find_one({"_id": ObjectId(user_id)})
        if not user:
            return jsonify({"detail": "User not found"}), 404

        user["_id"] = str(user["_id"])
        id_number_preview = generate_id_number()
        user["id_number_preview"] = id_number_preview
        
        # ============ CHANGED: Convert path to full URL ============
        profile_pic_path = user.get("profile_pic")
        if profile_pic_path:
            user["profile_pic"] = f"/photos/{profile_pic_path}"
        else:
            user["profile_pic"] = ""
        # ===========================================================

        return jsonify({"user": user}), 200

    except Exception as e:
        print(f"ERROR in get_user_details: {str(e)}")
        traceback.print_exc()
        return jsonify({"detail": f"Error: {str(e)}"}), 500


@admin_bp.route("/api/admin/approve-user", methods=["POST"])
def approve_user():
    try:
        data = request.get_json()
        user_id = data.get("user_id")
        password = data.get("password")
        current_level = data.get("current_level")
        upcoming_level = data.get("upcoming_level")

        if not user_id or not password:
            return jsonify({"detail": "Missing data"}), 400

        password = str(password)[:72]

        id_number = generate_id_number()
    
        if not is_strong_password(password):
            return jsonify({"error": "Password must be strong"}), 400

        hashed_password = get_password_hash(password)

        serial = generate_approval_serial()

        result = mongo.db.users.update_one(
            {"_id": ObjectId(user_id)},
            {
                "$set": {
                    "is_approved": True,
                    "is_rejected": False,
                    "id_number": id_number,
                    "approval_serial": serial,   # 
                    "password": hashed_password,
                    "plain_password": password,
                    "approved_at": now_ist(),
                    "current_level": current_level,
                    "upcoming_level": upcoming_level
                }
            }
        )

        if result.modified_count == 0:
            return jsonify({"detail": "Update failed"}), 500

        mongo.db.notifications.delete_many({
            "user_id": user_id,
            "type": "new_registration"
        })

        user = mongo.db.users.find_one({"_id": ObjectId(user_id)})

        whatsapp_message = (
            f"Welcome to One Trust Family!%0A%0A"
            f"Your ID: {id_number}%0A"
            f"Your Password: {password}%0A%0A"
            f"Thank you!"
        )

        whatsapp_url = f"https://wa.me/91{user.get('mobile')}?text={whatsapp_message}"

        return jsonify({
            "message": "User approved",
            "id_number": id_number,
            "mobile": user.get("mobile"),
            "full_name": user.get("full_name"),
            "whatsapp_url": whatsapp_url
        }), 200

    except Exception as e:
        print(f"ERROR in approve_user: {str(e)}")
        traceback.print_exc()
        return jsonify({"detail": f"Error: {str(e)}"}), 500



@admin_bp.route("/api/admin/reject-user", methods=["POST"])
def reject_user():
    try:
        data = request.get_json()
        user_id = data.get("user_id")
        reason = data.get("reason", "").strip()

        if not user_id:
            return jsonify({"detail": "User ID required"}), 400

        if not reason:
            return jsonify({"detail": "Rejection reason required"}), 400

        user = mongo.db.users.find_one({"_id": ObjectId(user_id)})
        if not user:
            return jsonify({"detail": "User not found"}), 404

        mongo.db.users.update_one(
            {"_id": ObjectId(user_id)},
            {
                "$set": {
                    "is_rejected": True,
                    "is_approved": False,
                    "rejected_at": now_ist(),
                    "rejection_reason": reason
                }
            }
        )

        mongo.db.notifications.delete_many({
            "user_id": user_id,
            "type": "new_registration"
        })

        whatsapp_message = (
            f"Hi,%0A"
            f"Your account has been rejected due to: {reason}"
        )

        whatsapp_url = f"https://wa.me/91{user.get('mobile')}?text={whatsapp_message}"

        return jsonify({
            "message": "User rejected",
            "whatsapp_url": whatsapp_url
        }), 200

    except Exception as e:
        print(f"ERROR in reject_user: {str(e)}")
        traceback.print_exc()
        return jsonify({"detail": "Server error"}), 500


@admin_bp.route("/api/admin/add-product", methods=["POST"])
@admin_login_required
def add_product():
    try:
        data = request.get_json()

        if not data:
            return jsonify({"detail": "No data provided"}), 400

        name = data.get("name", "").strip()
        price = data.get("price")
        image_base64 = data.get("image")  # CHANGED: renamed variable

        if not name or not price or not image_base64:
            return jsonify({"detail": "All fields are required"}), 400

        if price <= 0:
            return jsonify({"detail": "Price must be greater than 0"}), 400

        # ============ NEW: Insert product first to get ID ============
        product_document = {
            "name": name,
            "price": float(price),
            "image": None,  # Temporary, will update after saving image
            "created_at": now_ist()
        }

        result = mongo.db.products.insert_one(product_document)
        
        if not result.inserted_id:
            return jsonify({"detail": "Failed to add product"}), 500

        product_id = str(result.inserted_id)
        
        # Save image with product ID as filename
        image_path = save_product_image(product_id, image_base64)
        
        if not image_path:
            # Rollback: delete product if image save failed
            mongo.db.products.delete_one({"_id": result.inserted_id})
            return jsonify({"detail": "Failed to save product image"}), 500
        
        # Update product with image path
        mongo.db.products.update_one(
            {"_id": result.inserted_id},
            {"$set": {"image": image_path}}
        )
        # =============================================================

        return jsonify({
            "message": "Product added successfully",
            "product_id": product_id
        }), 200

    except Exception as e:
        print(f"ERROR in add_product: {str(e)}")
        traceback.print_exc()
        return jsonify({"detail": f"Error: {str(e)}"}), 500


@admin_bp.route("/api/products", methods=["GET"])
def get_products():
    try:
        products = list(mongo.db.products.find())

        for product in products:
            product["_id"] = str(product["_id"])
            
            # ============ CHANGED: Convert path to full URL ============
            image_path = product.get("image")
            if image_path:
                product["image"] = f"/photos/{image_path}"
            # ===========================================================

        return jsonify({"products": products}), 200

    except Exception as e:
        print(f"ERROR in get_products: {str(e)}")
        traceback.print_exc()
        return jsonify({"detail": f"Error: {str(e)}"}), 500


@admin_bp.route("/api/admin/delete-product/<product_id>", methods=["DELETE"])
@admin_login_required
def delete_product(product_id):
    try:
        # ============ NEW: Delete image file first ============
        product = mongo.db.products.find_one({"_id": ObjectId(product_id)})
        
        if product:
            delete_product_image(product_id)  # Delete image file
        # ======================================================
        
        result = mongo.db.products.delete_one({"_id": ObjectId(product_id)})

        if result.deleted_count == 0:
            return jsonify({"detail": "Product not found"}), 404

        return jsonify({"message": "Product deleted successfully"}), 200

    except Exception as e:
        print(f"ERROR in delete_product: {str(e)}")
        traceback.print_exc()
        return jsonify({"detail": f"Error: {str(e)}"}), 500