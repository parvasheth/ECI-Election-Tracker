import json

with open('../service_account.json', 'r') as f:
    creds = json.load(f)

toml_content = f"""[gcp_service_account]
type = "{creds['type']}"
project_id = "{creds['project_id']}"
private_key_id = "{creds['private_key_id']}"
private_key = '''{creds['private_key']}'''
client_email = "{creds['client_email']}"
client_id = "{creds['client_id']}"
auth_uri = "{creds['auth_uri']}"
token_uri = "{creds['token_uri']}"
auth_provider_x509_cert_url = "{creds['auth_provider_x509_cert_url']}"
client_x509_cert_url = "{creds['client_x509_cert_url']}"
universe_domain = "{creds.get('universe_domain', 'googleapis.com')}"
"""

with open('streamlit_secrets_copy_paste.txt', 'w') as f:
    f.write(toml_content)
