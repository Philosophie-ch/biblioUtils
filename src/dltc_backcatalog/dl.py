#from dataclasses import dataclass
#from typing import Literal, Tuple
#import requests
#from bs4 import BeautifulSoup
#import os


#@dataclass(frozen=True, slots=True)
#class Config:
    #login_url: str
    #pdf_page_url: str
    #download_dir: str
    #username: str
    #password: str


#INVALID_CREDENTIALS_TEXTS = ['Invalid username or password', 'Invalid credentials']


#def login(config: Config) -> requests.Session:

    #session = requests.Session()

    #login_data = {'username': config.username, 'password': config.password, 'submit': 'Login'}

    #response = session.post(config.login_url, data=login_data)

    #if response.status_code != 200 or any(text in response.text for text in INVALID_CREDENTIALS_TEXTS):
        #raise ValueError(f"Invalid credentials to login to '{config.login_url}' with username '{config.username}'")

    #return session
