import hashlib
import datetime
from urllib.parse import urlencode



REQUEST_URL='http://localhost:8000/api/payments/easypaisa/verify/'
POST_URL='https://easypaystg.easypaisa.com.pk/easypay/Index.jsf'

def generate_easypaisa_url(user, meeting_id, amount):
    store_id = 'YOUR_STORE_ID'
    hash_key = 'YOUR_HASH_KEY'
    post_url = POST_URL
    return_url = REQUEST_URL

    order_ref = f"EP{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"
    amount_str = f"{amount:.2f}"

    params = {
        "storeId": store_id,
        "amount": amount_str,
        "postBackURL": return_url,
        "orderRefNum": order_ref,
        "expiryDate": (datetime.datetime.now() + datetime.timedelta(minutes=15)).strftime("%Y%m%d%H%M%S"),
        "autoRedirect": "1",
        "emailAddr": user.email or "test@example.com",
    }

    hash_string = f"{store_id}&{order_ref}&{amount_str}&{return_url}&{hash_key}"
    params["secureHash"] = hashlib.sha256(hash_string.encode()).hexdigest().upper()

    return post_url + '?' + urlencode(params), order_ref
