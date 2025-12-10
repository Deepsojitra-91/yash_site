from flask import Blueprint, request, jsonify, render_template
from bson import ObjectId
from datetime import datetime, timedelta
import re
from extensions import mongo, pwd_context, is_strong_password
from extensions import user_login_required
from flask import session

user_bp = Blueprint('user', __name__)

def verify_password(plain_password: str, hashed_password: str):
    try:
        plain_password = plain_password[:72]
        return pwd_context.verify(plain_password, hashed_password)
    except Exception as e:
        print(f"Password verification error: {e}")
        return False

def get_password_hash(password: str):
    password = password[:72]
    return pwd_context.hash(password)

def now_ist():
    from datetime import timezone
    ist = timezone(timedelta(hours=5, minutes=30))
    return datetime.now(ist).replace(tzinfo=None)

def validate_mobile(mobile: str):
    return bool(re.match(r"^\d{10}$", mobile))

def validate_email(email: str):
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


@user_bp.route('/')
def index():
    return render_template('user/index.html')


@user_bp.route('/login')
def login_page():
    return render_template('user/login.html')


@user_bp.route('/register')
def register_step1_page():
    return render_template('user/register.html')


@user_bp.route('/register-success')
def register_success_page():
    return render_template('user/register-success.html')


@user_bp.route('/dashboard')
@user_login_required
def dashboard_page():
    return render_template('user/dashboard.html')


@user_bp.route('/change-password')
@user_login_required
def change_password_page():
    return render_template('user/change-password.html')


@user_bp.route('/products')
@user_login_required
def products_page():
    return render_template('user/products.html')


@user_bp.route('/create-account')
@user_login_required
def create_account_page():
    return render_template('user/create-account.html')


@user_bp.route('/switch-user')
@user_login_required
def switch_user_page():
    return render_template('user/switch-user.html')


@user_bp.route('/referal-users')
@user_login_required
def referal_users_page():
    return render_template('user/referal-users.html')


@user_bp.route('/profile-details')
@user_login_required
def profile_details_page():
    return render_template('user/profile-details.html')


@user_bp.route('/api/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"detail": "No data provided"}), 400

        id_number = data.get('id_number', '').strip()
        password = data.get('password', '').strip()

        if not id_number or not password:
            return jsonify({"detail": "ID Number and password are required"}), 400

        user = mongo.db.users.find_one({"id_number": id_number})

        if not user:
            return jsonify({"detail": "Account not found."}), 404

        if not user.get("is_approved"):
            return jsonify({"detail": "Your account is pending approval. Please wait 24-48 hours."}), 403

        if user.get("is_rejected"):
            return jsonify({"detail": "Your account has been rejected by admin."}), 403

        if not verify_password(password, user["password"]):
            return jsonify({"detail": "Incorrect password."}), 401

        session["user"] = {
            "id_number": user.get("id_number"),
            "full_name": user.get("full_name"),
            "mobile": user.get("mobile")
        }

        return jsonify({
            "message": "Login successful",
            "id_number": user.get("id_number"),
            "full_name": user.get("full_name"),
            "mobile": user.get("mobile"),
            "email": user.get("email", ""),
            "birth_date": user.get("birth_date"),
            "gender": user.get("gender"),
            "address": user.get("address"),
            "city": user.get("city"),
            "state": user.get("state"),
            "profile_pic": user.get("profile_pic"),
            "is_approved": user.get("is_approved", False),
            "is_rejected": user.get("is_rejected", False),
            "current_level": user.get("current_level", "-"),
            "upcoming_level": user.get("upcoming_level", "-")
        }), 200

    except Exception as e:
        print(f"Login error: {e}")
        return jsonify({"detail": "Server error occurred."}), 500


@user_bp.route('/api/complete-registration', methods=['POST'])
def complete_registration():
    try:
        data = request.get_json()

        if not data:
            return jsonify({"detail": "No data provided"}), 400

        mobile = data.get('mobile', '').strip()
        full_name = data.get('full_name', '').strip()
        email = data.get('email', '').strip()
        birth_date = data.get('birth_date', '').strip()
        gender = data.get('gender', '').strip()
        referral_code = data.get('referral_code', '').strip()
        address = data.get('address', '').strip()
        city = data.get('city', '').strip()
        state = data.get('state', '').strip()
        profile_pic = data.get('profile_pic')
        created_by_admin = data.get('created_by_admin', False)
        
        join_with_register = data.get('join_with_register', False)
        if isinstance(join_with_register, str):
            join_with_register = join_with_register == "1" or join_with_register.lower() == "true"

        print(f"🔍 DEBUG complete_registration:")
        print(f"   - mobile: {mobile}")
        print(f"   - created_by_admin: {created_by_admin}")
        print(f"   - join_with_register: {join_with_register} (type: {type(join_with_register)})")

        # Validate required fields
        if not all([mobile, full_name, birth_date, gender, address, city, state]):
            return jsonify({"detail": "All fields required except email"}), 400

        # Age validation
        birth = datetime.strptime(birth_date, '%Y-%m-%d')
        min_date = datetime.now() - timedelta(days=365 * 10)

        if birth > min_date:
            return jsonify({"detail": "Age must be at least 10 years"}), 400

        # Validate mobile and email
        if not validate_mobile(mobile):
            return jsonify({"detail": "Invalid mobile"}), 400

        if email and not validate_email(email):
            return jsonify({"detail": "Invalid email"}), 400
        
        # Skip duplicate check only when join_with_register is True
        if not join_with_register:
            print("⚠️ Checking for duplicate mobile (join_with_register is False)")
            
            existing_user = mongo.db.users.find_one({"mobile": mobile})
            if existing_user:
                print("❌ Duplicate mobile found! Blocking registration.")
                return jsonify({"detail": "Mobile already registered"}), 409

            if email:
                existing_email = mongo.db.users.find_one({"email": email})
                if existing_email:
                    print("❌ Duplicate email found! Blocking registration.")
                    return jsonify({"detail": "Email already registered"}), 409
        else:
            print("✅ Skipping duplicate check (join_with_register is True)")

        user_document = {
            "mobile": mobile,
            "full_name": full_name,
            "email": email or "", 
            "birth_date": birth_date,
            "gender": gender,
            "referral_code": referral_code if referral_code else None,
            "address": address,
            "city": city,
            "state": state,
            "profile_pic": profile_pic,
            "is_approved": False,  
            "is_rejected": False,
            "id_number": None,
            "password": None,
            "created_by_admin": created_by_admin,
            "created_at": now_ist(),
            "updated_at": now_ist()
        }

        result = mongo.db.users.insert_one(user_document)

        if not result.inserted_id:
            return jsonify({"detail": "Registration failed"}), 500

        print(f"   ✅ User registered successfully! ID: {result.inserted_id}")

        notification = {
            "type": "new_registration",
            "user_id": str(result.inserted_id),
            "mobile": mobile,
            "full_name": full_name,
            "created_by_admin": created_by_admin,
            "created_at": now_ist(),
            "read": False
        }

        mongo.db.notifications.insert_one(notification)
        
        # Different messages for admin vs user registration
        if created_by_admin:
            msg = "User registration request submitted successfully! Admin will review and approve within 24-48 hours."
        else:
            msg = "Registration successful! Your account will be approved within 24-48 hours."

        return jsonify({
            "message": msg,
            "user_id": str(result.inserted_id)
        }), 200

    except Exception as e:
        print(f"❌ Registration error: {e}")
        return jsonify({"detail": "Server error"}), 500
    

@user_bp.route('/api/validate-referral', methods=['POST'])
def validate_referral():
    try:
        data = request.get_json()
        referral_code = data.get("referral_code", "").strip()

        if referral_code == "":
            return jsonify({"valid": True}), 200

        user = mongo.db.users.find_one({"id_number": referral_code})

        if not user:
            return jsonify({"valid": False, "message": "Referral ID does not exist"}), 404

        if not user.get("is_approved"):
            return jsonify({"valid": False, "message": "Referral user is not approved yet"}), 400

        return jsonify({"valid": True}), 200

    except Exception:
        return jsonify({"valid": False, "message": "Server error"}), 500


@user_bp.route('/api/change-password', methods=['POST'])
def change_password():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"detail": "No data provided"}), 400

        mobile = data.get('mobile', '').strip()
        id_number = data.get('id_number', '').strip()
        old_password = data.get('old_password', '').strip()
        new_password = data.get('new_password', '').strip()

        if not mobile or not id_number or not old_password or not new_password:
            return jsonify({"detail": "All fields are required"}), 400

        if not is_strong_password(new_password):
            return jsonify({"detail": "Password must include uppercase, lowercase, number, special character and be 8+ chars"}), 400

        user = mongo.db.users.find_one({"mobile": mobile, "id_number": id_number})
        if not user:
            return jsonify({"detail": "Account not found"}), 404

        if not verify_password(old_password, user["password"]):
            return jsonify({"detail": "Current password is incorrect"}), 400

        if old_password == new_password:
            return jsonify({"detail": "New password must be different from current password"}), 400

        hashed_password = get_password_hash(new_password)

        result = mongo.db.users.update_one(
            {"mobile": mobile, "id_number": id_number},
            {
                "$set": {
                    "password": hashed_password,
                    "plain_password": new_password,
                    "updated_at": now_ist()

                }
            }
        )

        if result.modified_count == 0:
            return jsonify({"detail": "Password update failed"}), 500

        return jsonify({"message": "Password changed successfully"}), 200

    except Exception as e:
        print(f"Change password error: {e}")
        return jsonify({"detail": "Server error occurred"}), 500


@user_bp.route('/api/update-profile', methods=['POST'])
def update_profile():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"detail": "No data provided"}), 400

        mobile = data.get('mobile', '').strip()
        full_name = data.get('full_name', '').strip()
        profile_pic = data.get('profile_pic')

        if not mobile:
            return jsonify({"detail": "Mobile number is required"}), 400

        if not full_name:
            return jsonify({"detail": "Full name is required"}), 400

        update_data = {
            "full_name": full_name,
            "updated_at": now_ist()
        }

        if profile_pic:
            update_data["profile_pic"] = profile_pic

        result = mongo.db.users.update_one(
            {"mobile": mobile},
            {"$set": update_data}
        )

        if result.matched_count == 0:
            return jsonify({"detail": "User not found"}), 404

        updated_user = mongo.db.users.find_one({"mobile": mobile})

        return jsonify({
            "message": "Profile updated successfully",
            "user_name": updated_user.get("full_name"),
            "profile_pic": updated_user.get("profile_pic")
        }), 200

    except Exception as e:
        print(f"Update profile error: {e}")
        return jsonify({"detail": "Server error occurred"}), 500


@user_bp.route('/api/accounts/by-mobile', methods=['GET'])
def get_accounts_by_mobile():
    try:
        mobile = request.args.get('mobile', '').strip()
        if not mobile:
            return jsonify({"detail": "Mobile is required"}), 400

        users = mongo.db.users.find(
            {
                "mobile": mobile,
                "is_approved": True,
                "is_rejected": False
            },
            {
                "_id": 0,
                "id_number": 1,
                "current_level": 1,
                "upcoming_level": 1
            }
        )

        accounts = []
        for u in users:
            accounts.append({
                "id_number": u.get("id_number"),
                "current_level": u.get("current_level", "-"),
                "upcoming_level": u.get("upcoming_level", "-")
            })

        return jsonify({"accounts": accounts}), 200

    except Exception as e:
        print(f"get_accounts_by_mobile error: {e}")
        return jsonify({"detail": "Server error occurred"}), 500


@user_bp.route('/api/accounts/by-referral', methods=['GET'])
def get_accounts_by_referral():
    try:
        ref_id = request.args.get('ref_id', '').strip()
        if not ref_id:
            return jsonify({"detail": "Referral ID is required"}), 400

        users = mongo.db.users.find(
            {
                "referral_code": ref_id,
                "is_approved": True,
                "is_rejected": False
            },
            {
                "_id": 0,
                "id_number": 1,
                "current_level": 1,
                "upcoming_level": 1
            }
        )

        referrals = []
        for u in users:
            referrals.append({
                "id_number": u.get("id_number"),
                "current_level": u.get("current_level", "-"),
                "upcoming_level": u.get("upcoming_level", "-")
            })

        return jsonify({"accounts": referrals}), 200

    except Exception as e:
        print(f"get_accounts_by_referral error: {e}")
        return jsonify({"detail": "Server error occurred"}), 500


@user_bp.route('/api/account-by-id', methods=['GET'])
def account_by_id():
    try:
        id_number = request.args.get('id_number', '').strip()
        if not id_number:
            return jsonify({"detail": "ID Number is required"}), 400

        user = mongo.db.users.find_one({"id_number": id_number})
        if not user:
            return jsonify({"detail": "Account not found"}), 404

        if not user.get("is_approved"):
            return jsonify({"detail": "This account is not approved yet."}), 403

        if user.get("is_rejected"):
            return jsonify({"detail": "This account has been rejected by admin."}), 403

        return jsonify({
            "message": "Account loaded",
            "id_number": user.get("id_number"),
            "full_name": user.get("full_name"),
            "mobile": user.get("mobile"),
            "email": user.get("email", ""),
            "birth_date": user.get("birth_date"),
            "gender": user.get("gender"),
            "address": user.get("address"),
            "city": user.get("city"),
            "state": user.get("state"),
            "profile_pic": user.get("profile_pic"),
            "is_approved": user.get("is_approved", False),
            "is_rejected": user.get("is_rejected", False),
            "current_level": user.get("current_level", "-"),
            "upcoming_level": user.get("upcoming_level", "-")
        }), 200

    except Exception as e:
        print(f"account_by_id error: {e}")
        return jsonify({"detail": "Server error occurred"}), 500