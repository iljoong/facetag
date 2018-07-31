from datetime import datetime, timedelta
import base64
import hmac
import hashlib
import urllib

#https://github.com/yokawasa/azure-functions-python-samples/tree/master/blob-sas-token-generator
_AZURE_STORAGE_API_VERSION = "2016-05-31"

def generate_sas_token (storage_account, storage_key, permission, token_ttl, container_name, blob_name = None ):
    sp = permission
    # Set start time to five minutes ago to avoid clock skew.
    st= str((datetime.utcnow() - timedelta(minutes=5) ).strftime("%Y-%m-%dT%H:%M:%SZ"))
    se= str((datetime.utcnow() + timedelta(hours=token_ttl)).strftime("%Y-%m-%dT%H:%M:%SZ"))
    srt = 'o' if blob_name else 'co'

    # Construct input value
    inputvalue = "{0}\n{1}\n{2}\n{3}\n{4}\n{5}\n{6}\n{7}\n{8}\n".format(
        storage_account,  # 0. account name
        sp,                   # 1. signed permission (sp)
        'b',                  # 2. signed service (ss)
        srt,                  # 3. signed resource type (srt)
        st,                   # 4. signed start time (st)
        se,                   # 5. signed expire time (se)
        '',                   # 6. signed ip
        'https',              # 7. signed protocol
        _AZURE_STORAGE_API_VERSION)  # 8. signed version

    # Create base64 encoded signature
    hash =hmac.new(base64.b64decode(storage_key),inputvalue.encode("utf8"),hashlib.sha256).digest()
    sig = base64.b64encode(hash)

    querystring = {
        'sv':  _AZURE_STORAGE_API_VERSION,
        'ss':  'b',
        'srt': srt,
        'sp': sp,
        'se': se,
        'st': st,
        'spr': 'https',
        'sig': sig,
    }
    sastoken = urllib.parse.urlencode(querystring)

    sas_url = None
    if blob_name:
        sas_url = "https://{0}.blob.core.windows.net/{1}?{2}".format(
            storage_account,
            blob_name,
            sastoken)
    else:
        sas_url = "https://{0}.blob.core.windows.net/{1}?{2}".format(
            storage_account,
            container_name,
            sastoken)

    return {
            'token': sastoken,
            'url' : sas_url
           }

