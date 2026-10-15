"""Secrets store salted PBKDF2 hashes, not plaintext passwords."""
import hashlib,hmac,secrets,time

def hash_password(password):
    salt=secrets.token_hex(16);iterations=600000
    digest=hashlib.pbkdf2_hmac('sha256',password.encode(),salt.encode(),iterations).hex()
    return f'pbkdf2_sha256${iterations}${salt}${digest}'

def verify(password,encoded):
    try:
        scheme,count,salt,expected=encoded.split('$')
        if scheme!='pbkdf2_sha256' or not 100000<=int(count)<=2000000:return False
        actual=hashlib.pbkdf2_hmac('sha256',password.encode(),salt.encode(),int(count)).hex()
        return hmac.compare_digest(actual,expected)
    except (ValueError,AttributeError):return False

if __name__=='__main__':
    import getpass
    p=getpass.getpass('Yangi parol (kamida 12 belgi): ')
    if len(p)<12:raise SystemExit('Parol kamida 12 belgi bo‘lsin.')
    print(hash_password(p))
