import hashlib
import datetime
from urllib.parse import urlencode


RETURN_URL = 'http://localhost:8000/api/payments/jazzcash/verify/'
POST_URL = 'https://sandbox.jazzcash.com.pk/CustomerPortal/transactionmanagement/merchantform/'


def generate_jazzcash_url(user, amount):
    merchant_id = 'MC199733'
    password = 'YOUR_PASSWORD'
    integrity_salt = 'YOUR_SALT'
    return_url = RETURN_URL
    post_url = POST_URL

    txn_ref = f"JC{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"
    txn_date = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
    amount_paisa = str(int(amount * 100))

    params = {
        'pp_Version': '1.1',
        'pp_TxnType': 'MWALLET',
        'pp_Language': 'EN',
        'pp_MerchantID': merchant_id,
        'pp_Password': password,
        'pp_TxnRefNo': txn_ref,
        'pp_Amount': amount_paisa,
        'pp_TxnDateTime': txn_date,
        'pp_BillReference': 'ZoomClone',
        # 'pp_Description': f'Meeting ID: {}',
        'pp_ReturnURL': return_url,
    }

    hash_string = '&'.join([integrity_salt] + [params[k] for k in sorted(params)])
    secure_hash = hashlib.sha256(hash_string.encode()).hexdigest().upper()
    params['pp_SecureHash'] = secure_hash

    return post_url + '?' + urlencode(params), txn_ref
