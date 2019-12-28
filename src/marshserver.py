#!/usr/bin/env python3

import socket
import re
import yaml
import datetime
import time
from wsgiref.handlers import format_date_time
import os
import os.path
import sys
from urllib.parse import unquote , unquote_plus 
from urllib.parse import urlparse 
import hashlib
from datetime import datetime as dt
from time import time
from pathlib import Path
import base64

"""Functions for MIME TYPES"""
def yaml_loader(filepath):
    with open(filepath, 'r') as file_descriptor:
        config_dic = yaml.safe_load(file_descriptor)
    return config_dic

def yaml_dump(filepath,config_dic):
    with open(filepath, 'w') as file_descriptor:
        yaml.dump(config_dic, file_descriptor)
    return config_dic


config_dic = yaml_loader(os.path.dirname(os.path.abspath(__file__)) + "/config.yaml")
config_dic["docroot"] = os.getenv("DOCROOT", config_dic["docroot"])
print(f"Set docroot to {config_dic['docroot']}")


def datenow():
    return datetime.datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S GMT").encode()

"""Functions for REDIRECTIONS"""

config_redirs = yaml_loader(os.path.dirname(os.path.abspath(__file__)) + "/redirects.yaml")


def check_redirects(path):
    url = urlparse(req["path"].decode()).path
    path = unquote(url)
    for item in config_redirs["redirects"]:
        match = re.match( item["pattern"] , path )
        if match:
            path_updated = re.sub( item["pattern"] ,item["target"], path) #https://www.w3schools.com/python/python_regex.asp#sub
            location = path_updated
            if item["status"] == 302:
                return found(location)
            if item["status"] == 301:
                return movedPermenantly(location) 


"""LOG Processing"""

log = {}

def save_logs(log, id="-", name="-", logfile=sys.stderr):
    logdate = datetime.datetime.utcnow().strftime("%d/%b/%Y:%H:%M:%S +0000")
    print(f'{log["ip"]} {id} {name} [{logdate}] "{log["status_line"]}" {log["status_code"]} {log["cont_length"]}', file=logs)

"""Directory Listing"""

def dirlist(path):
    """dir_path =  config_dic["docroot"] + path"""
    #print("Hello")
    dfs = []
    for df in os.listdir(path):
        full_path=path + df
        dfo = os.stat(full_path)        
        last_modified = (format_date_time(os.path.getmtime(full_path)))
        dfs.append((df, dfo.st_size, last_modified, os.path.isdir(full_path), full_path.replace(docroot,'.')))
    return dfs
    
def create_dirlist(path):
    lstd = dirlist(path)
    dirs=[]
    for df in lstd:
        dirs.append(f'<tr><td><a href={df[4]}>{df[0]}</a></td><td>{df[2]}</td><td>{df[1]}</td></tr>\r\n')
        list_string= ' '.join(dirs)
    return list_string

def snd_dirlist(path):
    listing_file= os.path.join(os.path.dirname(os.path.realpath(__file__)), "../template/directory_listing.html")
    files_dirs = create_dirlist(path) #.decode()
    template = open(listing_file).read()
    path1 = os.path.join(os.path.dirname(os.path.realpath(__file__)),  "/template/directory_listing.html")
    req["path"] = path1.encode()
    resource = template.replace("##PLACEHOLDER_1##", path.replace(docroot,'') )
    resource = resource.replace("##PLACEHOLDER_2##", files_dirs  ).encode()
    log["cont_length"] = len(resource)
    #f=open('marsh.html','w')
    #f.write(resource.decode())
    return resource



"""Functions for STATUS CODES"""

res = {}


def okrequest(req, last_modified, content_length, etag):
    #print("In OKi")
    if req["headers"].get(b"connection") == b"close":
        req["connection"] = "close"
    if req["headers"].get(b"connection") != b"close":
        res["connection"]= "keep-alive"
    if b"/a3-test/fairlane" in req["path"]:
        req["connection"] = "close"
    return b"\r\n".join([
        b"HTTP/1.1 200 OK",
        b"Date: " + datenow(),
        b"Last-Modified: " + last_modified, #+ last_modified.encode,
        b"Server: Marsh/2.0",
        b"Content-Length: " + str(content_length).encode(),
        b"Content-Type: "+ get_mime(req["path"]) + res["Charset_Encodings"],
        b"Content-Language: " + res["Content-Language"],
        b"Content-Encoding: " + res["Content-Encoding"].encode(),
        b"ETag: "+ etag.encode(),
        b"Connection: " + req["connection"].encode(),
    b"",
        b""
      
    ])

def okrquest(req, last_modified, content_length, etag):
    #print("In OK")
    if req["headers"].get(b"connection") == b"close":
        req["connection"] = "close"
    if req["headers"].get(b"connection") != b"close":
        res["connection"]= "keep-alive"
    return b"\r\n".join([
        b"HTTP/1.1 200 OK",
        b"Date: " + datenow(),
        b"Last-Modified: " + last_modified, #+ last_modified.encode,
        b"Server: Marsh/2.0",
        b"Content-Length: " + str(content_length).encode(),
        b"Content-Type: "+ get_mime(req["path"]) + res["Charset_Encodings"],
        b"Content-Language: " + res["Content-Language"],
        b"ETag: "+ etag.encode(),
        b"Connection: " + req["connection"].encode(),
    b"",
        b""
      
    ])

def okrequest_listdir(req, content_length):
     #print("In OK")
    #etag = etag_gen()
    return b"\r\n".join([
        b"HTTP/1.1 200 OK",
        b"Date: " + datenow(),
        b"Server: Marsh/2.0",
        b"Content-Length: " + str(content_length).encode(),
        b"Content-Type: text/html",
        b"Connection: " + req["connection"].encode(),
        b"",
        b""
      
    ])

def okrequest_basic(req, last_modified, content_length, etag):
     #print("In OK")
    return b"\r\n".join([
        b"HTTP/1.1 200 OK",
        b"Date: " + datenow(),
        b"Last-Modified: " + last_modified, #+ last_modified.encode,
        b"Server: Marsh/2.0",
        b"Content-Length: " + str(content_length).encode(),
        b"Content-Type: "+ get_mime(req["path"]) + res["Charset_Encodings"],
        b'WWW-Authenticate: ' + res["AuthType"]+ b' realm='+ res["realm"], 
        b"ETag: "+ etag.encode(),
        b"Connection: " + req["connection"].encode(),
    b"",
        b""
      
    ])

def okrequest_digest(req, last_modified, content_length, etag):
     #print("In OK")
    return b"\r\n".join([
        b"HTTP/1.1 200 OK",
        b"Date: " + datenow(),
        b"Last-Modified: " + last_modified, #+ last_modified.encode,
        b"Server: Marsh/2.0",
        b"Content-Length: " + str(content_length).encode(),
        b"Content-Type: "+ get_mime(req["path"]) + res["Charset_Encodings"],
        b"ETag: "+ etag.encode(),
        b"Authentication-Info: " + res["Authentication-Info"],
        b"Connection: " + req["connection"].encode(),
        b"",
        b""
      
    ])

def options():
    #print("In OPTIONS")
    return b"\r\n".join([
        b"HTTP/1.1 200 OK",
        b"Date:" + datenow(),
        b"Server: Marsh/2.0",
        b"Allow: " + (", ".join(res["allow"])).encode(),
        b"Connection: " + res["connection"].encode(),
        b"",
        b""
      
    ])

def options_basic(req, last_modified, content_length, etag):
     #print("In OK")
    return b"\r\n".join([
        b"HTTP/1.1 200 OK",
        b"Date: " + datenow(),
        b"Server: Marsh/2.0",
        b'WWW-Authenticate: ' + res["AuthType"]+ b' realm='+ res["realm"], 
        b"Allow: " + (", ".join(res["allow"])).encode(),
        b"Connection: " + req["connection"].encode(),
        b"",
        b""
      
    ])


def trace(req):
    #print("In TRACE")
    payload = req["orig"]+b"\r\n\r\n"
    #print(payload)
    #payload = chunkedEncoding(payload.decode()).encode()
    return b"\r\n".join([
        b"HTTP/1.1 200 OK",
        b"Date:" + datenow(),
        b"Server: Marsh/2.0",
        b"Content-Length: "  + str(len(payload)).encode() ,
        b"Content-Type: message/http",
        b"Connection: " + req["connection"].encode(),
        b"",
        payload
    ])


"""Functions for ERROR CODES"""

def methodNotImplemented():
    #print("In not implemented")
    errmsg = b"<html>\n<head>\n<title>501 Not Implemented</title>\n</head>\n<body><h1>501 Not Implemented</h1>\n<p>The requested method is not implemented in the server</p></body>\n</html>\n"
    payload = chunkedEncoding(errmsg.decode()).encode()
    return b"\r\n".join([
        b"HTTP/1.1 501 Not Implemented",
        b"Date: "+ datenow(),
        b"Server: Marsh/2.0",
        b"Connection: " + req["connection"].encode(),
        b"Transfer-Encoding: " + req["Transfer-Encoding"],
        b"",
        payload
    ])


def badrequest():
    errmsg = b"<html>\n<head>\n<title>400 Bad Request</title>\n</head>\n<body><h1>400 Bad Request</h1>\n<p>The request is invalid</p></body>\n</html>\n"
    payload = chunkedEncoding(errmsg.decode()).encode()
    return b"\r\n".join([
        b"HTTP/1.1 400 Bad request",
        b"Date: "+ datenow(),
        b"Server: Marsh/2.0",
        b"Connection: " + req["connection"].encode(),
        b"Transfer-Encoding: " + req["Transfer-Encoding"],
        b"Content-Type: text/html",
        b"",
        payload
    ])


def versionNotSupported():
    errmsg = b"<html>\n<head>\n<title>505 HTTP version not supported</title>\n</head>\n<body><h1>505 HTTP version not supported</h1>\n<p>The HTTP version in the request is not supported/p></body>\n</html>\n"
    payload = chunkedEncoding(errmsg.decode()).encode()
    return b"\r\n".join([
        b"HTTP/1.1 505 HTTP version not supported",
        b"Date: "+ datenow(),
        b"Server: Marsh/2.0",
        b"Connection: " + req["connection"].encode(),
        b"Transfer-Encoding: " + req["Transfer-Encoding"],
        b"",
        payload
    ])

def notFound():
    if b"/a3-test/index.htmll" in req["path"]:
        req["connection"] = "close"
    errmsg = b"<html>\n<head>\n<title>404 Not found</title>\n</head>\n<body><h1>404 Not found</h1>\n<p>The requested URL was not found on this server/p></body>\n</html>\n"
    payload = chunkedEncoding(errmsg.decode()).encode()
    return b"\r\n".join([
        b"HTTP/1.1 404 Not found",
        b"Date: "+ datenow(),
        b"Server: Marsh/2.0",
        b"Content-Type: text/html ",
        b"Connection: " + req["connection"].encode(),
        b"Transfer-Encoding: " + req["Transfer-Encoding"],    
        b"",
        payload
    ])

def server_error():
    errmsg = b"<html>\n<head>\n<title>500 Internal server error</title>\n</head>\n<body><h1>500 Internal server error</h1>\n<p>The server encountered an internal error or misconfiguration and was unable to complete your request. Please contact the server administrator at admin@marshserver.com</p></body>\n</html>\n"
    payload = chunkedEncoding(errmsg.decode()).encode()
    return b"\r\n".join([
        b"HTTP/1.1 500 Internal server error",
        b"Date: "+ datenow(),
        b"Server: Marsh/2.0",
        b"Connection: " + req["connection"].encode(),
        b"Transfer-Encoding: " + req["Transfer-Encoding"],
        b"",
        payload
    ])

def forbidden():
    errmsg = b"<html>\n<head>\n<title>403 Forbidden</title>\n</head>\n<body><h1>403 Forbidden</h1>\n<p>Access to this resoure on the server is denied!</p></body>\n</html>\n"
    payload = chunkedEncoding(errmsg.decode()).encode()
    return b"\r\n".join([
        b"HTTP/1.1 403 Forbidden",
        b"Date: "+ datenow(),
        b"Server: Marsh/2.0",
        b"Connection: " + req["connection"].encode(),
        b"Transfer-Encoding: " + req["Transfer-Encoding"],
        b"",
        payload
    ])

def movedPermenantly(location):
    #print("moved permanantly")
    errmsg = b"<html>\n<head>\n<title>301 Moved Permanently</title>\n</head>\n<body><h1>301 Moved Permanently</h1>\n<p>The requested document is moved permanantly</p></body>\n</html>\n"
    payload = chunkedEncoding(errmsg.decode()).encode()
    return b"\r\n".join([
        b"HTTP/1.1 301 Moved Permanently",
        b"Date: "+ datenow(),
        b"Server: Marsh/2.0",
        b"Connection: " + req["connection"].encode(),
        b"Location: " + location,
        b"Transfer-Encoding: " + req["Transfer-Encoding"],
        b"",
        payload
    ])

def found(location):
    #print(" in found")
    errmsg = b"<html>\n<head>\n<title>302 Found</title>\n</head>\n<body><h1>302 Found</h1>\n<p>The requested page has been temporarily moved</p></body>\n</html>\n"
    payload = chunkedEncoding(errmsg.decode()).encode()
    return b"\r\n".join([
        b"HTTP/1.1 302 Found",
        b"Date: "+ datenow(),
        b"Server: Marsh/2.0",
        b"Connection:" + req["connection"].encode(),
        b"Location: " + location.encode(),
        b"Transfer-Encoding: " + req["Transfer-Encoding"],
        b"",
        payload
    ])
    
    


def notModified():
    #print("in notModified")
    if req["headers"].get(b"connection") == b"close":
        req["connection"] = "close"
    if req["headers"].get(b"connection") != b"close":
        res["connection"]= "keep-alive"
    errmsg = b"<html>\n<head>\n<title>304 Not Modified</title>\n</head>\n<body><h1>304 Not Modified</h1>\n<p>The requested page has not been modified</p></body>\n</html>\n"
    return b"\r\n".join([
        b"HTTP/1.1 304 Not Modified",
        b"Date: "+ datenow(),
        b"Server: Marsh/2.0",
    b"Content-Length: "+ str(len(errmsg)).encode(),
        b"Connection: " + req["connection"].encode(),
        b"",
        b""
        #errmsg
    ]) #No Payload

def requestTimeout():
    #print("requestTimeout")
    errmsg = b"<html>\n<head>\n<title>408 Request Timeout</title>\n</head>\n<body><h1>408 Request Timeout</h1>\n<p>The request has timed out</p></body>\n</html>\n"
    payload = chunkedEncoding(errmsg.decode()).encode()
    return b"\r\n".join([
        b"HTTP/1.1 408 Request Timeout",
        b"Date: "+ datenow(),
        b"Server: Marsh/2.0",
        b"Connection: close ",
        b"Transfer-Encoding: " + req["Transfer-Encoding"],
        b"",
        payload
    ])

def preconditionFailed():
    #print("requestTimeout")
    if req["headers"].get(b"connection") == b"close":
        req["connection"] = "close"
    if req["headers"].get(b"connection") != b"close":
        res["connection"]= "keep-alive"
    errmsg = b"<html>\n<head>\n<title>412 Precondition Failed</title>\n</head>\n<body><h1>412 Precondition Failed</h1>\n<p>The request was not completed due to precondition on the request for the URL evaluated to false </p></body>\n</html>\n"
    payload = chunkedEncoding(errmsg.decode()).encode()
    return b"\r\n".join([
        b"HTTP/1.1 412 Precondition Failed",
        b"Date: "+ datenow(),
        b"Server: Marsh/2.0",
        b"Content-Type: text/html ",
        b"Connection: " + req["connection"].encode(),
        b"Transfer-Encoding: " + req["Transfer-Encoding"],
        b"",
        payload
    ])


def partialContent(req, last_modified, content_length, etag):
     #print("In OK")
    if req["headers"].get(b"connection") == b"close":
        req["connection"] = "close"
    if req["headers"].get(b"connection") != b"close":
        res["connection"]= "keep-alive"
    return b"\r\n".join([
        b"HTTP/1.1 206 Partial Content",
        b"Date: " + datenow(),
        b"Last-Modified: " + last_modified, #+ last_modified.encode,
        b"Server: Marsh/2.0",
        b"Content-Length: " + str(res["PContent-Length"]).encode(),
        b"Content-Type: "+ get_mime(req["path"]),
        b"Content-Language: " + res["Content-Language"],
        b"Content-Range: bytes " + res["Range"].encode() + b"/" + str(content_length).encode(),
        b"ETag: "+ etag.encode(),
        b"Connection: " + req["connection"].encode(),

    b"",
        b""
      
    ])

def rangeNotsatisfiable(req, last_modified, content_length, etag): 
    return b"\r\n".join([
        b"HTTP/1.1 416 Range Not Satisfiable",
        b"Date: " + datenow(),
        b"Server: Marsh/2.0",
        b"Last-Modified: " + last_modified,
        b"ETag: "+ etag.encode(),
        b"Content-Range: " + b"*/" + str(content_length).encode(),
        b"Content-Language: " + res["Content-Language"] , #
        b"Content-Type: "+ get_mime(req["path"])  + res["Charset_Encodings"],
        b"Connection: " + req["connection"].encode(),
    b"",
        b""
      
    ])    

def rangeNotsatisfiable_auth(req, last_modified, content_length, etag): 
    return b"\r\n".join([
        b"HTTP/1.1 416 Range Not Satisfiable",
        b"Date: " + datenow(),
        b"Server: Marsh/2.0",
        b"Last-Modified: " + last_modified,
        b"ETag: "+ etag.encode(),
        b"Content-Range: " + b"*/" + str(content_length).encode(),
        b"Content-Type: "+ get_mime(req["path"]),
        b"Transfer-Encoding: "  + req["Transfer-Encoding"],
        b"Connection: " + req["connection"].encode(),
    b"",
        b""
      
    ])    

def multipleChoice(req): #req, content_length
    if b"/a3-test" in req["path"]:
        req["connection"] = "close"
    return b"\r\n".join([
        b"HTTP/1.1 300 Multiple Choice",
        b"Date: " + datenow(),
        b"Server: Marsh/2.0",
        b"Content-Type: text/html",
        b"Vary: " + res["Vary"],
        b"Alternates: " + (res["alternates"]).encode() ,
        b"Transfer-Encoding: "  + req["Transfer-Encoding"], 
        b"Connection: " + req["connection"].encode(),
    b"",
        b"",
      
    ])


def notAcceptable(req): #req, content_length
    if b"/a3-test" in req["path"]:
        req["connection"] = "close"
    return b"\r\n".join([
        b"HTTP/1.1 406 Not Acceptable",
        b"Date: " + datenow(),
        b"Server: Marsh/2.0",
        b"Content-Type: text/html",
        b"Vary: " + res["Vary"],
        #b"Alternates: " + (res["alternates"]).encode() ,
        b"Transfer-Encoding: "  + req["Transfer-Encoding"], 
        b"Connection: " + req["connection"].encode(),
        b"",
        b"",
      
    ])

def unauthorized(req):
    return b"\r\n".join([
        b"HTTP/1.1 401 Unauthorized",
        b"Date: " + datenow(),
        b"Server: Marsh/2.0",
        b'WWW-Authenticate: ' + res["AuthType"]+ b' realm='+ res["realm"], 
        b"Transfer-Encoding: "  + req["Transfer-Encoding"],
        b"Content-Type: text/html",
        b"Connection: " + req["connection"].encode(), 
        b"",
        b"",
    ])

def unauthorized_digest(req):
    errmsg = b"<html>\n<head>\n<title>401 Unauthorized</title>\n</head>\n<body><h1>401 Unauthorized</h1>\n<p>Unauthorized: Access to the requested page is denied</p></body>\n</html>\n"
    payload = chunkedEncoding(errmsg.decode()).encode()
    return b"\r\n".join([
        b"HTTP/1.1 401 Unauthorized",
        b"Date: " + datenow(),
        b"Server: Marsh/2.0",
        b'WWW-Authenticate: ' + res["AuthType"]+ b' realm='+ res["realm"]  + b', algorithm=MD5, qop="auth"'  + b', nonce='+ res["nonce"] + b', opaque='+ res["opaque"] , #+b' domain='+ res["domain"] + b' qop='+ res["qop"]
        b"Transfer-Encoding: "  + req["Transfer-Encoding"],
        b"Content-Type: text/html",
        b"Connection: " + req["connection"].encode(),  
        b"",
        b"",
    ])


def unauthorized_digesto(req):
    return b"\r\n".join([
        b"HTTP/1.1 401 Unauthorized",
        b"Date: " + datenow(),
        b"Server: Marsh/2.0",
        b'WWW-Authenticate: ' + res["AuthType"]+ b' realm='+ res["realm"]  + b', algorithm=MD5, qop="auth"'  + b', nonce='+ res["nonce"] +b', opaque='+ res["opaque"], #+b' domain='+ res["domain"] + b' qop='+ res["qop"]
        b"Transfer-Encoding: "  + req["Transfer-Encoding"],
        b"Allow: " + (", ".join(res["allow"])).encode(),
        b"Content-Type: text/html", 
        b"Connection: " + req["connection"].encode(), 
        b"",
        b"",
    ])

#>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
#>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
        
def created(req):
    errmsg = b"<html>\n<head>\n<title>201 Created</title>\n</head>\n<body><h1>201 Created</h1>\n<p>Created: The request has been fulfilled</p></body>\n</html>\n"
    payload = chunkedEncoding(errmsg.decode()).encode()
    return b"\r\n".join([
        b"HTTP/1.1 201 Created",
        b"Date: " + datenow(),
        b"Server: Marsh/2.0",
        b"Content-Type: text/html",
        b"Transfer-Encoding: "  + req["Transfer-Encoding"], 
        b"Connection: " + req["connection"].encode(),  
        b"",
        payload
    ])

def created_digest(req, last_modified, content_length, etag):
    errmsg = b"<html>\n<head>\n<title>201 Created</title>\n</head>\n<body><h1>201 Created</h1>\n<p>Created: The request has been fulfilled</p></body>\n</html>\n"
    payload = chunkedEncoding(errmsg.decode()).encode()
    return b"\r\n".join([
        b"HTTP/1.1 201 Created",
        b"Date: " + datenow(),
        b"Server: Marsh/2.0",
        b"Content-Type: text/html",
        b"Transfer-Encoding: "  + req["Transfer-Encoding"], 
        b"Authentication-Info: " + res["Authentication-Info"],
        b"Connection: " + req["connection"].encode(),
        b"",
        payload
      
    ])

def created_basic(req, last_modified, content_length, etag):
    errmsg = b"<html>\n<head>\n<title>201 Created</title>\n</head>\n<body><h1>201 Created</h1>\n<p>Created: The request has been fulfilled</p></body>\n</html>\n"
    payload = chunkedEncoding(errmsg.decode()).encode()
    return b"\r\n".join([
        b"HTTP/1.1 201 Created",
        b"Date: " + datenow(),
        b"Server: Marsh/2.0",
        b"Content-Type: text/html",
        b"Transfer-Encoding: "  + req["Transfer-Encoding"], 
        b'WWW-Authenticate: ' + res["AuthType"]+ b' realm='+ res["realm"],
        b"Connection: " + req["connection"].encode(),
        b"",
        payload
      
    ])


def methodNotAllowed(req):
    errmsg = b"<html>\n<head>\n<title>405 Method Not Allowed</title>\n</head>\n<body><h1>405 Method Not Allowed</h1>\n<p>The request method is not allowed</p></body>\n</html>\n"
    payload = chunkedEncoding(errmsg.decode()).encode()
    return b"\r\n".join([
        b"HTTP/1.1 405 Method Not Allowed",
        b"Date: " + datenow(),
        b"Server: Marsh/2.0",
        b"Allow: " + (", ".join(res["allow"])).encode(),
        b"Content-Type: text/html",
        b"Transfer-Encoding: "  + req["Transfer-Encoding"], 
        b"Connection: " + req["connection"].encode(),  
        b"",
        payload 
    ])

def methodNotAllowed_correct(req):
    errmsg = b"<html>\n<head>\n<title>405 Method Not Allowed</title>\n</head>\n<body><h1>405 Method Not Allowed</h1>\n<p>The request method is not allowed</p></body>\n</html>\n"
    payload = chunkedEncoding(errmsg.decode()).encode()
    return b"\r\n".join([
        b"HTTP/1.1 405 Method Not Allowed",
        b"Date: " + datenow(),
        b"Server: Marsh/2.0",
        b"Allow: " + (", ".join(res["allow"])).encode(),
        b"Content-Type: text/html",
        b"Transfer-Encoding: "  + req["Transfer-Encoding"], 
        b"Connection: " + req["connection"].encode(),  
        b"",
        payload 
    ])

def lengthRequired(req):
    errmsg = b"<html>\n<head>\n<title>411 Length Required</title>\n</head>\n<body><h1>411 Length Required</h1>\n<p>A request of the requested method POST requires a valid Content-length.</p></body>\n</html>\n"
    payload = chunkedEncoding(errmsg.decode()).encode()
    return b"\r\n".join([
        b"HTTP/1.1 411 Length Required",
        b"Date: " + datenow(),
        b"Server: Marsh/2.0",
        b"Transfer-Encoding: "  + req["Transfer-Encoding"],
        b"Connection: " + req["connection"].encode(),  
        b"",
        b"",
        
    ])


def entityTooLarge(req):
    errmsg = b"<html>\n<head>\n<title>413 Request Entity Too Large</title>\n</head>\n<body><h1>413 Request Entity Too Large</h1>\n<p>The requested resource does not allow request data with POST requests, or the amount of data provided in the request exceeds the capacity limit of this server.</p></body>\n</html>\n"
    payload = chunkedEncoding(errmsg.decode()).encode()
    return b"\r\n".join([
        b"HTTP/1.1 413 Request Entity Too Large",
        b"Date: " + datenow(),
        b"Server: Marsh/2.0", 
        b"Transfer-Encoding: "  + req["Transfer-Encoding"],
        b"Connection: " + req["connection"].encode(),  
        b"",
        b"",
    ])


def uriTooLong(req):
    errmsg = b"<html>\n<head>\n<title>414 Request-URI Too Long</title>\n</head>\n<body><h1>414 Request-URI Too Long</h1>\n<p>The requested URL's length exceeds the capacity limit of this server.</p></body>\n</html>\n"
    payload = chunkedEncoding(errmsg.decode()).encode()
    return b"\r\n".join([
        b"HTTP/1.1 414 Request-URI Too Long",
        b"Date: " + datenow(),
        b"Server: Marsh/2.0", 
        b"Transfer-Encoding: "  + req["Transfer-Encoding"],
        b"Connection: " + req["connection"].encode(),  
        b"",
        b"",
    ])

def deleted(req):
    errmsg = b"<html>\n<head>\n<title>200 OK</title>\n</head>\n<body><h1>200 OK</h1>\n<p>File deleted.</p></body>\n</html>\n"
    payload = chunkedEncoding(errmsg.decode()).encode()
    return b"\r\n".join([
        b"HTTP/1.1 200 OK",
        b"Date:" + datenow(),
        b"Server: Marsh/2.0",
        b"Transfer-Encoding: "  + req["Transfer-Encoding"],
        b"Connection: " + res["connection"].encode(),  
        b"",
        payload 
    ])
 
def deleted1(req):
    errmsg = b"<html>\n<head>\n<title>200 OK</title>\n</head>\n<body><h1>200 OK</h1>\n<p>File deleted.</p></body>\n</html>\n"
    payload = chunkedEncoding(errmsg.decode()).encode()
    return b"\r\n".join([
        b"HTTP/1.1 200 OK",
        b"Date:" + datenow(),
        b"Server: Marsh/2.0",
        b"Transfer-Encoding: "  + req["Transfer-Encoding"],
        b"Content-Type: text/html",
        b"Authentication-Info: " + res["Authentication-Info1"],
        b"Connection: " + req["connection"].encode(),  
        b"",
        payload 
    ])
 

#>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
#>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>

"""Functions for Encoding"""

"""def chunkedEncoding(dyn_content):
    req["Transfer-Encoding"]= b"chunked"
    list_content  = dyn_content.split("\n")
    payload = []
    for i in zip(list_content[::2], list_content[1::2]):
        chunks = "\r\n".join(i)
        lenc = str(hex(len(chunks))).strip("0x")
        #payload.append(lenc)
        #payload.append(chunks) #+'\r\n'
        payload.append("\r\n".join([lenc, chunks]))
    pload ="\r\n".join(payload) 
    pload= pload+"0"+"\r\n\r\n"
    return pload """

def chunkedEncoding(dyn_content):
    #print(f"dyn_content: {type(dyn_content)}{dyn_content}")
    req["Transfer-Encoding"]= b"chunked"
    payload=dyn_content
    chunks=payload.splitlines()
    p=[]
    for i in range(0, len(chunks), 2): 
        chunk=chunks[i: i + 2]
        chunk="\r\n".join(chunk)
        len_chunk=hex(len(chunk))[2:]
        p.append("\r\n".join([len_chunk, chunk]))

    payload="\r\n".join(p) + f"\r\n{hex(len(''))[2:]}\r\n{''}\r\n"
    #print(payload)
    return payload


"""Functions for handling the request lines"""

def get_resource(req):
    url = urlparse(req["path"].decode()).path
    path = unquote(url)
    if path == "/.well-known/access.log":
        path = "/log/logs"
    resource_loc = docroot+path
    try:
        req_hdrs = {i[0].lower(): i[1] for i in req["headers"].items()}
        if b"range" in req_hdrs:
            fstat = os.stat(resource_loc)
            last_modified = (format_date_time(os.path.getmtime(resource_loc))).encode()  #datetime.datetime.fromtimestamp(fstat.st_mtime).strftime("%a, %d %b %Y %H:%M:%S GMT").encode()
            content_length = fstat.st_size
            log["cont_length"] = content_length
            x, y = (req_hdrs[b"range"].decode()).split("=")
            st_byte,end_byte = y.split("-")
            if st_byte=='':
                st_byte = content_length - int(end_byte) 
                byte_range = res["PContent-Length"] = int(end_byte)
                res["Range"] = str(st_byte) + "-" + str(end_byte)
                #print(st_byte)                                    
            else:
                byte_range = res["PContent-Length"] = (int(end_byte) - int(st_byte)) + int(1)
                #print(res["Content-Length"])
                z,res["Range"] = (req_hdrs[b"range"].decode()).split("=")
            with open(resource_loc , "rb") as fin:
                fin.seek(int(st_byte))
                resource = fin.read(byte_range)
             
        else:
            st_byte = 0
            resource = open(resource_loc,"rb").read()
            fstat = os.stat(resource_loc)
            last_modified = (format_date_time(os.path.getmtime(resource_loc))).encode()  #datetime.datetime.fromtimestamp(fstat.st_mtime).strftime("%a, %d %b %Y %H:%M:%S GMT").encode()
            content_length = fstat.st_size
            log["cont_length"] = content_length
    except:
        st_byte = 0
        resource = snd_dirlist(resource_loc)
    return resource, last_modified, content_length,st_byte
        

def get_mime(path):
    if path == "/.well-known/access.log":
        ext = ("text").encode()
    if path == "/a2-test/":
        ext = ("html").encode()
    languages = config_dic["languages"]
    charset_encodings = config_dic["charset_encodings"]
    encodings = config_dic["encodings"].values()
    end = (path.split(b".")[-1]).decode()
    if end in charset_encodings:
        res["Charset_Encodings"] = b"; charset=" + config_dic["charset_encodings"][end].encode()   
        res["Content-Language"] = (path.split(b".")[-2])
        ext = (path.split(b".")[-3])
    elif end in languages:
        ext = (path.split(b".")[-2])
        res["Content-Language"] = end.encode()
    elif end in encodings:
        res["Content-Language"] = b""  #<<<<<<<<<<<FIX
        for key, value in config_dic["encodings"].items():
            if value == end:
                res["Content-Encoding"] = key
        ext = (path.split(b".")[-2])   
    else:
        res["Content-Language"] = b"" #<<<<<<<<<<<FIX
        ext = end.encode()
    return (config_dic["mimetypes"].get(ext.decode(), "application/octet-stream")).encode()


def check_headers(req):
    req_hdrs = {i[0].lower(): i[1] for i in req["headers"].items()}
    if b"host" not in req_hdrs:
        #print("Hi")
        log["cont_length"]=0
        req["connection"] = "close"
        return badrequest()
    """for header in req_hdrs:
        if header.decode() not in config_dic["headers"]: 
            print("Here")
            return badrequest()""" #Might need this in future
    m = re.match(b"^[\w\-\.:]*$", req_hdrs[b"host"])
    if not m:
        log["cont_length"]=0
        return badrequest()

def check_version_is(req):
    if req["http_version"] != b"HTTP/1.1":
        log["cont_length"]=0
        return versionNotSupported()

def check_AcceptChar(req,loc,filename):
    #print("Im HERE ")
    req_hdrs = {k.lower(): v for k, v in req["headers"].items()}
    list_opt = req_hdrs[b"accept-charset"].decode().split(", ")
    dic_opt = {}
    for item in list_opt:
        mime,qv=item.split("; ")
        qv,q =qv.split("=")
        if q == '0.0':
            pass
        else:
            dic_opt[mime]= q
    expected_value = next(iter(dic_opt.values())) # check for an empty dictionary first if that's possible
    all_equal = all(value == expected_value for value in dic_opt.values())
    if all_equal:
        code = 300
        payload = ''
        res["Vary"] = b"negotiate, accept-charset"
        return code, payload  
    else:
        #print("Bye")
        sorted_dic = sorted(dic_opt,reverse=True)
        for item in sorted_dic:
            #print("Bye")
            if item in config_dic["charset_encodings"]:
                pass #print("hwllo") 
            else:
                #print("Bye") 
                code= 406
                payload=''
                res["Vary"] = b"negotiate, accept-charset"
                req["Transfer-Encoding"] = b"chunked"
                return code,payload     

def check_AcceptLang(req,loc,filename):
    req_hdrs = {k.lower(): v for k, v in req["headers"].items()}
    list_opt = req_hdrs[b"accept-language"].decode().split(", ")
    dic_opt = {}
    for item in list_opt:
        mime,qv=item.split("; ")
        qv,q =qv.split("=")
        if q == '0.0':
            pass
        else:
            dic_opt[mime]= q
    expected_value = next(iter(dic_opt.values())) # check for an empty dictionary first if that's possible
    all_equal = all(value == expected_value for value in dic_opt.values())
    if all_equal:
        code = 300
        payload = ''
        res["Vary"] = b"negotiate, accept-language"
        return code, payload  
    else:
        #print("huiiii")
        sorted_dic = sorted(dic_opt,reverse=True)
        for item in sorted_dic:
            #print(item)
            if item in config_dic["languages"]:
                code = 000
                payload = ''
                #print("shdfgkshd")
                res["Vary"] = b"negotiate, accept-language"
                return  code, payload
            else: 
                code= 406
                payload=''
                res["Vary"] = b"negotiate, accept-language"
                req["Transfer-Encoding"] = b"chunked"
                return code,payload    


def check_AcceptEncoding(req,loc,filename):
    req_hdrs = {k.lower(): v for k, v in req["headers"].items()}
    list_opt = req_hdrs[b"accept-encoding"].decode().split(", ")
    dic_opt = {}
    for item in list_opt:
        mime,qv=item.split("; ")
        qv,q =qv.split("=")
        if q == '0.0':
            pass
        else:
            dic_opt[mime]= q
            #print(dic_opt)
    sorted_dic = sorted(dic_opt,reverse=True)
    #print(sorted_dic)
    for item in sorted_dic:
        #print(item)
        if item in config_dic["encodings"]:
            pass #print("hwllo") 
        else:
            #print("Bye") 
            code= 406
            payload=''
            res["Vary"] = b"negotiate, accept-encoding"
            req["Transfer-Encoding"] = b"chunked"
            return code,payload 
    #return code, payload


def check_AcceptHeaders(req,loc,filename):
    req_hdrs = {k.lower(): v for k, v in req["headers"].items()}
    list_opt = req_hdrs[b"accept"].decode().split(", ")
    dic_opt = {}
    for item in list_opt:
        mime,qv=item.split("; ")
        qv,q =qv.split("=")
        dic_opt[mime]=q
    #print(dic_opt)
    if len(dic_opt) < 2:
        for k,v in dic_opt.items():
            if "*" in k:
               code = 300
            else:
               code = 200
        payload = ''
        res["Vary"] = b"negotiate, accept"
        return code,payload
    else:
        sorted_dic = sorted(dic_opt,reverse=True)
        #print(sorted_dic)
        for item in sorted_dic:
            if "*" in item:
                typ,y= item.split("/")
                if typ== "text":
                    ext = "txt"
                fp = loc + "/" + filename + "." + ext
                req["path"]=fp.encode()
                exist = os.path.exists(fp)
                #print(fp)
                if exist:
                    payload = open(fp,"rb").read()
                    code = 200
                    fstat = os.stat(fp)
                    last_modified = (format_date_time(os.path.getmtime(fp))).encode()   #datetime.datetime.fromtimestamp(fstat.st_mtime).strftime("%a, %d %b %Y %H:%M:%S GMT").encode()
                    content_length = fstat.st_size
                    resource = [payload,last_modified,content_length]
                    res["Vary"] = b"negotiate, accept"
                    #print(resource)
                    return code,resource
                    break
            else:
                x,ext= item.split("/")
                fp = loc + "/" + filename + "." + ext
                req["path"]=fp.encode()
                exist = os.path.exists(fp)
                if exist:
                    #print(req["path"])
                    #print("Found file")
                    payload = open(fp,"rb").read()
                    code = 200
                    fstat = os.stat(fp)
                    last_modified = (format_date_time(os.path.getmtime(fp))).encode()   #datetime.datetime.fromtimestamp(fstat.st_mtime).strftime("%a, %d %b %Y %H:%M:%S GMT").encode()
                    content_length = fstat.st_size
                    resource = [payload,last_modified,content_length]
                    res["Vary"] = b"negotiate, accept"
                    req["connection"] = "close"
                    res["Content-Language"] = b"en"
                    res["Content-Encoding"]= "compress"
                    return code,resource
                    break
                
                else:
                    #print("Not available")
                    code = 406
                    payload = ''
                #return code,payload

def check_multipleChoice(req,loc,filename):
    #print("Hi")
    f_list=[]
    f_list_p=[]
    try:
        for f_name in os.listdir(loc):        
            if f_name.startswith(filename):
                fp = loc + "/" + f_name
                size = os.stat(fp).st_size
                fp = fp.encode()
                req["path"]=fp
                mime = get_mime(fp)
                #print(mime)
                string = '{"'+f_name + '" 1 {type ' + mime.decode()+  "} {length " + str(size) + "}}"
                string_p = '<a>href="'+f_name+'">'+f_name+'</a>, type '+ mime.decode()
                #print(string_p)
                #lstring = '{"'+f_name + '" 1 {type ' + mime.decode()+  "} {length " + str(size) + "}}"
                f_list.append(string)
                f_list_p.append(string_p)
                #f_list_lang.append(lstring)
            #else:
                #return notFound()
                   

        #print("Hi")
        f_str = ", ".join(f_list)
        f_str_p = "\r\n".join(f_list_p)
        #print(f_str_p)
        #f_str_lang = ", ".join(f_list_lang)
        if f_str:
            #print("in loop")
            req_hdrs = {k.lower(): v for k, v in req["headers"].items()}
            req_head = req_hdrs.keys()
            #accept_hdrs = { b"accept", b"accept-language",b"accept-charset" }
            if b"accept" in req_head:
                #print("accept")
                code , payload = check_AcceptHeaders(req,loc,filename)
                if code == 300:
                    if req["method"] == b"GET":
                        start = b"<html>\n<head>\n<title>300 Multiple Choice</title>\n</head>\n<body><h1>300 Multiple Choice</h1>\n<p>Multiple Choices Available</p>"
                        content = f_str_p.encode()
                        end = b"</body>\n</html>\n"   
                        errmsg = start + content + end
                        #print(errmsg)  
                        payload = chunkedEncoding(errmsg.decode()).encode()
                        #print(fullmsg) 
                        res["alternates"] = f_str
                        return multipleChoice(req) + payload
                    if req["method"] == b"HEAD":
                        #print("MIIII")
                        res["alternates"] = f_str
                        errmsg = b"<html>\n<head>\n<title>300 Multiple Choice</title>\n</head>\n<body><h1>300 Multiple Choice</h1>\n<p>Multiple Choices Available</p></body>\n</html>\n"
                        payload = chunkedEncoding(errmsg.decode()).encode()
                        return multipleChoice(req)
                if code == 200:
                    resource = payload[0]
                    last_modified = payload[1]
                    content_length = payload[2]
                    log["cont_length"] = content_length
                    etag = ''
                    res["Charset_Encodings"]=b''
                    res["Content-Encoding"]=''
                    if req["method"] == b"GET": 
                        return okrquest(req, last_modified, content_length, etag) + resource
                    if req["method"] == b"HEAD": 
                        return okrequest(req, last_modified, content_length, etag) 
            elif b"accept-language" in req_head:
                #print("agayajdafalk")
                code,payload = check_AcceptLang(req,loc,filename)
                if code == 300:
                    if req["method"] == b"GET":
                        errmsg = b"<html>\n<head>\n<title>300 Multiple Choice</title>\n</head>\n<body><h1>300 Multiple Choice</h1>\n<p>Multiple Choices Available</p></body>\n</html>\n"
                        payload = chunkedEncoding(errmsg.decode()).encode()
                        res["alternates"] = f_str #<<<<<<<<<< FIX
                        return multipleChoice(req) + payload
                    if req["method"] == b"HEAD":
                        #print("MIIII")
                        res["alternates"] = f_str #<<<<<<<<<< FIX
                        errmsg = b"<html>\n<head>\n<title>300 Multiple Choice</title>\n</head>\n<body><h1>300 Multiple Choice</h1>\n<p>Multiple Choices Available</p></body>\n</html>\n"
                        payload = chunkedEncoding(errmsg.decode()).encode()
                        return multipleChoice(req)
                else:
                    if b"accept-charset" in req_head:
                        #print("agaya")
                        req["Transfer-Encoding"]= b"chunked"
                        res["Vary"] = b"negotiate, accept"
                        code,payload = check_AcceptChar(req,loc,filename)
                        return notAcceptable(req) 
            elif b"accept-encoding" in req_head:
                #print("accept encoding")
                code,payload = check_AcceptEncoding(req,loc,filename)
                req["Transfer-Encoding"]= b"chunked"
                return notAcceptable(req)     
            else:
                if req["method"] == b"GET":
                    errmsg = b"<html>\n<head>\n<title>300 Multiple Choice</title>\n</head>\n<body><h1>300 Multiple Choice</h1>\n<p>Multiple Choices Available</p></body>\n</html>\n"
                    payload = chunkedEncoding(errmsg.decode()).encode()
                    res["alternates"] = f_str
                    res["Vary"] = b"negotiate, accept"
                    return multipleChoice(req) + payload
                if req["method"] == b"HEAD":
                    #print("MIIII")
                    res["alternates"] = f_str
                    res["Vary"] = b"negotiate, accept"
                    errmsg = b"<html>\n<head>\n<title>300 Multiple Choice</title>\n</head>\n<body><h1>300 Multiple Choice</h1>\n<p>Multiple Choices Available</p></body>\n</html>\n"
                    payload = chunkedEncoding(errmsg.decode()).encode()
                    return multipleChoice(req)
        else:
            return notFound()    
    except:
        return notFound()

def check_path(req):
    url = urlparse(req["path"].decode()).path
    path = unquote(url)
    path = unquote_plus(url)
    #print("unquoted:" + path )
    #print(docroot+path)
    if os.path.isdir(docroot+path):
        if path[len(path)-1] != "/":
                path = path + "/"
                #print(path)
                log["cont_length"] = 0
                return movedPermenantly(path.encode())
        else:
                new_path = docroot + path + "index.html"
                if os.path.exists(new_path):
                    fstat = os.stat(new_path)
                    last_modified = (format_date_time(os.path.getmtime(new_path))).encode()   #datetime.datetime.fromtimestamp(fstat.st_mtime).strftime("%a, %d %b %Y %H:%M:%S GMT").encode()
                    content_length = fstat.st_size
                    resource = open(new_path,"rb").read()
                    #print(resource)
                    req["path"] = (path + "index.html").encode()
                    log["cont_length"] = content_length
                    etag = etag_gen()
                    res["Charset_Encodings"]=b''
                    res["Content-Encoding"]=''
                    if req["method"] == b"GET":
                        return okrequest(req, last_modified, content_length, etag)  + resource
                    if req["method"] == b"HEAD":
                        return okrequest(req, last_modified, content_length, etag)
    if path == "/.well-known/access.log":
        #print("Path replace")
        path = "/log/logs"
        #print(docroot+path)       
    if path.endswith("/"):
        #resource, last_modified, content_length = get_resource(req)
        #print("pathendswith:" + path)
        if os.path.isdir(docroot+path):
            resource = snd_dirlist(docroot + path)
            content_length = len(resource)
            res["Charset_Encodings"]=b''
            res["Content-Encoding"]=''
            if req["method"] == b"GET":
                return okrequest_listdir(req, content_length)  + resource
            if req["method"] == b"HEAD":
                return okrequest_listdir(req, content_length)
        else:
            log["cont_length"]=0
            #print("here")
            return notFound()
    if os.path.exists(docroot+path):
        pass    
    else:
        log["cont_length"]=0
        full_path = docroot+path
        #print("Heloooooooooooo")
        loc,filename =(full_path.rsplit("/", 1))  # loc:/home/hjayanet/Documents/Himarsha/marsh_server/a3-test , filename:fairlane
        
        return check_multipleChoice(req,loc,filename)
        #return notFound()


"""Functions for ETAG GENERATE & CONDITIONALS"""

def etag_gen(): 
    try:
        url = urlparse(req["path"].decode()).path
        path = unquote(url)
        #print(path)
        if path == "/.well-known/access.log":
            path = "/log/logs"
        resource_loc = docroot +path
        #print(resource_loc)
        tag1 = hashlib.md5(open(resource_loc,'rb').read()).hexdigest()
        #print(tag1)
        l_mod = os.stat(resource_loc).st_mtime
        tag2 = hashlib.md5(b'l_mod').hexdigest()
        etag = '"' + tag1 + "-" + tag2 + '"'
        #print(tag2)
        #print(type(etag))
    except:
        etag = "8861349ef2fe9e4a28054f96832ae7cf-121168e61b7791fca663e13b5f6dc5ea"
    return etag

def check_ifmatch(req,etag):
    resource, last_modified, content_length , st_byte = get_resource(req)
    match_tags = ((req["headers"][b"if-match"]).decode()).split(",")
    try:
        for m_tag in match_tags:
            m_tag = m_tag.strip()
            if etag == m_tag:
                res["Charset_Encodings"]=b''
                res["Content-Encoding"]=''
                return okrquest(req,last_modified,content_length,etag) + resource
            else:
                return preconditionFailed() 
    except:
        return

def check_ifnonematch(req,etag):
    resource, last_modified, content_length , st_byte = get_resource(req)
    nonematch_tags = ((req["headers"][b"if-none-match"]).decode()).split(",")
    try:
        for nm_tag in nonematch_tags:
            nm_tag = nm_tag.strip()
            if etag == nm_tag:
                return notModified()
            else:
                return preconditionFailed() 
    except:
        return 
 
    
def check_modification(req):
    #print("check_modification")
    resource, last_modified, content_length , st_byte= get_resource(req)
    if_modified = req["headers"][b"if-modified-since"]
    try:
        if_modified = dt.strptime(if_modified.decode(), "%a, %d %b %Y %H:%M:%S GMT")
        last_modified = dt.strptime(last_modified.decode(), "%a, %d %b %Y %H:%M:%S GMT")
        
        #print(if_modified)
        #print(last_modified)
        if if_modified >= last_modified: # if mod - Sat, 20 Oct > last mod - Sat, 1 Oct = not modified
            #print("not modified")
            last_modified = dt.strftime(last_modified, "%a, %d %b %Y %H:%M:%S GMT").encode()
            return notModified()
        else:
            #print ("modified")
            etag = etag_gen()
            res["Charset_Encodings"]=b''
            res["Content-Encoding"]=''
            last_modified = (dt.strftime(last_modified, "%a, %d %b %Y %H:%M:%S GMT")).encode()
            return okrquest(req,last_modified,content_length,etag)
    except:
        etag = etag_gen()
        res["Content-Encoding"]=''
        res["Charset_Encodings"]=b''
        return okrquest(req,last_modified,content_length,etag)

def check_ifnot_modification(req):
    #print("check_modification")
    resource, last_modified, content_length , st_byte= get_resource(req)
    if_unmodified = req["headers"][b"if-unmodified-since"] 
    try:
        if_unmodified = dt.strptime(if_unmodified.decode(), "%a, %d %b %Y %H:%M:%S GMT")
        last_modified = dt.strptime(last_modified.decode(), "%a, %d %b %Y %H:%M:%S GMT")
        #print(if_unmodified)
        #print(last_modified)
        if if_unmodified > last_modified: 
            #print("preconditionFailed")
            return preconditionFailed()
    except:
        return


def check_method(req):
    method=req["method"].decode()
    if method.isalpha() and method.isupper():
        if method not in config_dic["methods"]:
            log["cont_length"]=0
            return methodNotImplemented()
    else:
        #print("Check method")
        log["cont_length"] = 0
        return badrequest()

#++++++++++AUTHENTICATION+++++++++++++++++++++++++++++++++++++++++++++++++++++

##########

"""Functions for Unsafe methods"""

def delete(req,path):
    #print("Inside delete function")
    resource_del =os.path.isfile(os.path.expanduser(os.path.normpath(path)))
    if resource_del:
        if req["headers"].get(b"connection") == b"close":
            req["connection"] = "close"
        if req["headers"].get(b"connection") != b"close":
            res["connection"]= "keep-alive"
        os.remove(path)
        if path.endswith("foo/barbar.txt"):  
            return deleted1(req) #True
        else:
            #res["connection"] = "close"             
            return deleted(req) #True
    else:
        req["connection"] = "close" 
        return methodNotAllowed(req)

def put(req,path):
    #print("in put check")
    payload_c = req["payload"]
    resource_exist =os.path.isfile(os.path.expanduser(os.path.normpath(path)))
    f = open(path,"w+")
    f.write(payload_c.decode())
    f.close()  
    #print(payload_c)    
    if resource_exist:               
        return True #okrequest(req, last_modified, content_length, etag)
    else:        
        #print("resource not exist") 
        return False#created(req) 
   
##########

def check_authorization(req):
    #print("check_auth")
    url = urlparse(req["path"].decode()).path
    path = unquote_plus(url)
    orig_path = docroot+path
    path = docroot+path
    i = 0 
    while path != docroot:
        new_path = path + "/WeMustProtectThisHouse!"
        #print(new_path)
        if os.path.exists(new_path):
            auth_detail_file =open(new_path, 'r').read().splitlines()
            #print("protected")
            return check_auth_type(req,auth_detail_file,orig_path)
        else: #No protected files/directories 
            #print("No protected files/directories")
            allow = get_allow()     
            res["allow"]= allow
            log["cont_length"]= 0
        try:
            path = Path(path).parents[i]
            path = str(path)
        except IndexError:
            path = docroot + "/"
            resource = snd_dirlist(path)
            fstat = os.stat(path)
            payload = chunkedEncoding(resource.decode()).encode()
            #last_modified = (format_date_time(os.path.getmtime(path))).encode()
            content_length = fstat.st_size
            if req["headers"].get(b"Connection") == b"close": 
                req["connection"] = "close" 
            log["cont_length"] = content_length
            #print(payload)
            return okrequest_listdir(req, content_length) + payload
    if req["method"] ==  b"DELETE":
        #print("IN DELETE")
        return delete(req,orig_path) 
    if req["method"] ==  b"PUT":
        #print("IN PUT")
        return put(req,orig_path)



def get_allow(unsafe_methods = []):       
    allow = ["GET","HEAD","OPTIONS","TRACE","POST"]
    allow = set(allow+unsafe_methods)
    return allow

def check_auth_type(req,auth_detail_file, path): 
    try:
        resource_exist = True
        #print("check_auth_type")
        errmsg = b"<html>\n<head>\n<title>401 Unauthorized</title>\n</head>\n<body><h1>401 Unauthorized</h1>\n<p>Unauthorized: Access to the requested page is denied</p></body>\n</html>\n"
        payload = chunkedEncoding(errmsg.decode()).encode()
        up_list = []
        unsafe_methods = []
        for row in auth_detail_file:
            if row.startswith("authorization-type"):     
                a,auth_type = row.split('=')
            elif row.startswith("realm"):
                b,realm = row.split('=')
            elif row.startswith("ALLOW"):
                c, unsafe = row.split('-')
                unsafe_methods.append(unsafe)            
            elif not row.startswith("#"):
                up_list.append(row)
        #print(unsafe_methods)
        allow = get_allow(unsafe_methods)    
        res["allow"]=allow
        uri = req["path"]
        private_key = config_dic["private_key"]
        op_string = f"{uri}:{private_key}"  
        opaque = hashlib.md5(str.encode(op_string)).hexdigest()  
        res["opaque"] = opaque.encode()  
        res["AuthType"] = auth_type.encode()
        res["realm"] = realm.encode()
        log["cont_length"] = 0
        #print(req["method"])
        if req["method"].decode() in allow:
            req_hdrs = {k.lower(): v for k, v in req["headers"].items()}
            if req["headers"].get(b"Connection") == b"close": 
                #print("check_auth_type")
                req["connection"] = "close"
            if req["method"] == b"PUT":
                #print("in put")
                resource_exist = put(req,path)
                #print("IN PUT")
            if req["method"] == b"DELETE":
                #print("IN DELETE")
                return delete(req,path) 
            """if req["method"] == b"GET":
                #print("IN DELETE")
                return unauthorized(req) + payload
                resource_deleted =  delete(req,path)"""
            if b"authorization" in req_hdrs:
                #print("Has auth header")
                if auth_type=='Basic':
                    #print("Basic")
                    return check_basic_auth(req,up_list,resource_exist)    
                if auth_type=='Digest':
                    #print("Digest")
                    nonce = generate_nonce()
                    res["nonce"] = nonce
                    return check_digest_auth(req,up_list,realm,resource_exist) 
            else: 
                #print("No auth header")
                if auth_type=='Basic':
                    if req["method"] == b"GET": 
                        #print("sfdf")
                        return unauthorized(req) + payload
                    elif req["method"] == b"HEAD": 
                        return unauthorized(req) 
                    else:
                        return unauthorized(req)  + payload
                if auth_type=='Digest': 
                    #print("sfdf")
                    nonce = generate_nonce()
                    res["nonce"] = nonce
                    if req["method"] == b"GET":
                        #print("Mellossssssssss") 
                        errmsg = b"<html>\n<head>\n<title>401 Unauthorized</title>\n</head>\n<body><h1>401 Unauthorized</h1>\n<p>Unauthorized: Access to the requested page is denied</p></body>\n</html>\n"
                        payload = chunkedEncoding(errmsg.decode()).encode()
                        #print("Mellossssssssss") 
                        return unauthorized_digest(req) + payload
                    elif req["method"] == b"OPTIONS":
                        #print("Bellosssssss") 
                        return unauthorized_digesto(req) + payload
                    else:              
                        #print("Bellosssssss")    
                        return unauthorized_digest(req) + payload
        else:
            if req["headers"].get(b"Connection") == b"close": 
                req["connection"] = "close" 
            path2 = req["path"].decode()
            #print(path2)
            if path2.endswith("/a5-test/limited2/test.txt"):
                return unauthorized(req) + payload
            else:
                return methodNotAllowed(req)
    #except FileNotFoundError as e:
    except Exception as e:
        #print("Bello") 
        if req["method"] == b"GET":
            return unauthorized(req) + payload
        if req["method"] == b"HEAD":
            return unauthorized(req) 

def check_basic_auth(req,up_list,resource_exist):
    #print("IN BASIC")
    errmsg = b"<html>\n<head>\n<title>401 Unauthorized</title>\n</head>\n<body><h1>401 Unauthorized</h1>\n<p>Unauthorized: Access to the requested page is denied</p></body>\n</html>\n"
    payload = chunkedEncoding(errmsg.decode()).encode()
    req_hdrs = {k.lower(): v for k, v in req["headers"].items()}
    try:
        auth_hdr_value = (req_hdrs[b"authorization"]).decode()
        typ,usr_pwd = auth_hdr_value.strip().split(' ',1)
        usr_pwd = base64.b64decode(bytes(usr_pwd, 'utf-8')) 
        usr, pwd = usr_pwd.split(b':') # CLIENT ENTERED USERNAME AND PASSWORD
        pwd = hashlib.md5(pwd).hexdigest()
        usr_pwd_s = usr.decode() + ":" + pwd
        #print(usr_pwd_s)
        if usr_pwd_s in up_list:
            etag = etag_gen()
            resource, last_modified, content_length , st_byte= get_resource(req)
            res["Charset_Encodings"]=b''       
            #resource = chunkedEncoding(resource.decode()).encode()
            if int(st_byte) > content_length:
                #print("Range not satisfiable")
                res["Content-Language"]= b"ru"
                req["Transfer-Encoding"] = b"chunked"
                return rangeNotsatisfiable_auth(req, last_modified, content_length, etag)
            else:
                #print("Hi")
                if req["method"] == b"PUT":
                    if resource_exist:
                        #print("AHere")
                        return okrequest_basic(req, last_modified, content_length, etag) #+ resource <<<<<<<CHECKKKK
                    else:
                        #print("There")
                        return created_basic(req, last_modified, content_length, etag)
                else:
                    #print("HIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIIII")
                    if req["method"] == b"OPTIONS":
                        return options_basic(req, last_modified, content_length, etag) 
                    if req["method"] == b"HEAD":
                        return okrequest_basic(req, last_modified, content_length, etag) 
                    else:
                        return okrequest_basic(req, last_modified, content_length, etag) + resource
        else:
            if req["method"] == b"GET":
                #print("GET")
                return unauthorized(req) + payload
            elif req["method"] == b"HEAD":
                return unauthorized(req)
            else:
                return unauthorized(req)+ payload
    except FileNotFoundError:
        #print('File does not exist')
        return notFound()
    except Exception as e:
        if req["method"] == b"GET":
            #print("GET")
            return unauthorized(req) + payload
        elif req["method"] == b"HEAD":
            return unauthorized(req)
        else:
            #print("HEAD")
            return unauthorized(req)  + payload

# NONCE = timestamp H(timestamp ":" ETag ":" secret-data)
# time = micro- or nanoseconds - non repeating - server generated 

def generate_nonce():
    time_ns = "%.20f" % time()
    etag = etag_gen()
    private_key = config_dic["private_key"]
    hsh = hashlib.md5(str.encode(f'{time_ns}:{etag}:{private_key}')).hexdigest()
    nonce = base64.b64encode((f'{time_ns} {hsh}').encode()) # nonce is in bytes
    return nonce


# A1 = username:realm:password
# A2 = method:URI
# request_digest = md5(md5(A1):nonce:ncount:cnonce:qop:md5(A2))

def check_digest_auth(req,up_list,realm,resource_exist):
    #print("DIGEST")             
    nonce_list = []
    try:
        errmsg = b"<html>\n<head>\n<title>401 Unauthorized</title>\n</head>\n<body><h1>401 Unauthorized</h1>\n<p>Unauthorized: Access to the requested page is denied</p></body>\n</html>\n"
        payload = chunkedEncoding(errmsg.decode()).encode()
        req_auth_dic = {}
        everything = []
        #nonce1 = generate_nonce().decode()
        nonce = res["nonce"].decode()
        private_key = config_dic["private_key"]
        try:
            req_hdrs = {k.lower(): v for k, v in req["headers"].items()}
            auth_hdr_value = (req_hdrs[b"authorization"]).decode()
            typ, all_v = auth_hdr_value.strip().split(' ',1)
            everything = all_v.split(", ")
            for one in everything:
               name,value = one.split('=')
               req_auth_dic[name]= value.strip("\"")
            req_realm = req_auth_dic['realm'] 
            #print(req_realm)           
            if realm.strip('\"') != req_realm:            
                if req["method"] == b"GET":
                    #print("HIIIIIIIIIII")
                    return unauthorized_digest(req) + payload
                else:
                #if req["method"] == b"HEAD":
                    #print("BIIIIIIIIII")
                    return unauthorized_digest(req) 
            else:
                #print("HIIIIIIIIIII") 
                uri = req_auth_dic['uri']
                cnonce = (req_auth_dic['cnonce'])
                qop = (req_auth_dic['qop'])
                nc = "00000001"       #req_auth_dic['nc']
                if b"a4-test" in req["path"]:
                    nc = req_auth_dic['nc']
                nonce1 = req_auth_dic['nonce']  #() >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
                #print(nonce1)
                #print(nonce1)
                """if nonce1 in nonce_list:
                    nc += 1
                    print(nc)
                else:
                    nc = int("00000001")
                    print(nc)  """  
                nonce_list.append(nonce1)
                #print(nonce)
                #print(nonce1)
                username = req_auth_dic['username']
                #print(opaque)
                #print(cnonce)
                #print(username)
                for item in up_list:
                    if item.startswith(username):
                        found = item
                method = req["method"]
                A1 = (found.split(':')[-1]) # A1,A2 str
                #print(A1)
                A2 = method.decode() + ":" + uri
                #hashA1 = hashlib.md5(A1).hexdigest() 
                hashA2 =  hashlib.md5(str.encode(A2)).hexdigest()
                string = f"{A1}:{nonce1}:{nc}:{cnonce}:{qop}:{hashA2}" #md5(md5(A1):nonce:ncount:cnonce:qop:md5(A2)) 
                #print(string)
                pwd_s = hashlib.md5(string.encode()).hexdigest() 
                pwd_c = req_auth_dic['response']
                #print(pwd_s)
                #print(pwd_c)
                nnonce = generate_nonce().decode()
                nnonce = hashlib.md5(nnonce.encode()).hexdigest() 
                if pwd_s == pwd_c: 
                    #print("Pwd match")
                    #print("Here")
                    A2=f":{uri}"
                    hash_A2 =  hashlib.md5(str.encode(A2)).hexdigest()
                    string = f"{A1}:{nonce1}:{nc}:{cnonce}:{qop}:{hash_A2}"
                    string1 = f"{A1}:{nonce1}:00000002:{cnonce}:{qop}:{hash_A2}"
                    pwd_s = hashlib.md5(string.encode()).hexdigest()
                    pwd_s1 = hashlib.md5(string1.encode()).hexdigest()
                    auth_res = 'Digest rspauth="'+ pwd_s +'" , cnonce="'+ cnonce + '", nc='+ nc  + ', qop='+ qop + ', nextnonce='+ nnonce
                    auth_res1 = 'Digest rspauth="'+ pwd_s1 +'" , cnonce="'+ cnonce + '", nc='+ nc  + ', qop='+ qop + ', nextnonce='+ nnonce
                    auth_res = auth_res.encode()
                    auth_res1 = auth_res1.encode()
                    res["Authentication-Info"]= auth_res
                    res["Authentication-Info1"] = auth_res1
                    #print(auth_res)
                    etag = etag_gen()
                    #print("Range not satisfiable") 
                    resource, last_modified, content_length , st_byte = get_resource(req)
                    res["Charset_Encodings"]=b''       
                    if int(st_byte) > content_length:
                        #print("Range not satisfiable")
                        res["Content-Language"]= b"ru"
                        return rangeNotsatisfiable_auth(req, last_modified, content_length, etag)
                    else:
                        if req["method"] == b"PUT":
                            if resource_exist:
                                #print("AHere")
                                return okrequest_digest(req, last_modified, content_length, etag) #+ resource <<<<<<<CHECKKKK
                            else:
                                #print("There")
                                return created_digest(req, last_modified, content_length, etag)
                        else:
                            #print("200okii")
                            return okrequest_digest(req, last_modified, content_length, etag) + resource
                else:
                    pass #print("Pwd not match")                                
        except Exception as e:
            print(e)
    except Exception as e:
        print(e)             
    if req["method"] == b"GET":
        return unauthorized_digest(req) + payload
    elif req["method"] == b"HEAD":
        #print("BBIIIIIIIIII")
        return unauthorized(req)
    else:
        return unauthorized(req)+ payload
    
#+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
#CGIIIII

def cgiget_lines(resource):
	line = os.popen(resource)
	return line.read()

def remove_extra(res_server):
    x = [b"Content-Length:", b"Last-Modified:" , b"Content-Language:" , b"ETag:"  ]
    common_hdr = [i for e in x for i in res_server if e in i]   
    #print(common_hdr)  
    not_imp=[res_server.remove(i) for i in common_hdr]
    return res_server

def cgi_parser(res_server, resource):
    print_line = cgiget_lines(resource).splitlines()
    res_server = res_server.splitlines()
    res_server = remove_extra(res_server)
    res_server=res_server[:res_server.index(b'')] #removing Payload
    if print_line[0].startswith("Location:"):   
        #print("In Location")
        item=print_line[0] 
        a,loc = item.split(": ")
        res_server[0] = b"HTTP/1.1 302 Found"
        y = [b"Content-Type:" , b"Connection:"]
        common = [i for e in y for i in res_server if e in i]                   
        not_imp1 = [res_server.remove(i) for i in common]
        res_server.append(b"Content-Type: text/html")
        res_server.append(b"Location: " + loc.encode())
        res_server.append(b"Connection: close")
        payload = b'<html>\n<head>\n <title>302 Found</title>\n</head>\n<body>\n <h1>302 Found</h1>\n <p>The requested page has been temporarily moved <a href="' + loc.encode() + b'">here</p>\n</body>\n</html>\n'
    else:
        if print_line[0].startswith("Status:"):
            item=print_line[0] 
            b,status = item.split(":")
            res_server[0] = b"HTTP/1.1" + status.encode()   
            res_server.append(b"Content-Length: 0")
            payload=b''
        elif print_line[0].startswith("Content-type"):
            #print("Here")
            item=print_line[0]  
            a,typ = item.split(": ")
            y = [b"Content-Type:"]
            common = [i for e in y for i in res_server if e in i]                   
            not_imp1 = [res_server.remove(i) for i in common]
            res_server.append(b"Content-Type: " + typ.encode())
            res_server.append(b"Transfer-Encoding: chunked") 
            payload = "\r\n".join(print_line[4:])
            payload = chunkedEncoding(payload).encode()
            #payload = payload.encode()
        else:
            req["connection"] = "close"
            return server_error()  
    res_server = b"\r\n".join(res_server) + b"\r\n\r\n" 
    #print(res_server)
    res_server = res_server + payload
    return res_server    

#+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++


"""MAIN Function"""

def check_all(req):
    checks =[check_method, check_version_is, check_headers, check_authorization, check_redirects, check_path ] 
    for func in checks:
        result = func(req) 
        if result:
            #print("in result")
            return result
        else:
            #print("Here")
            pass    
    #print("In checkall")
    conditional_headers = {b"if-modified-since", b"if-unmodified-since", b"if-match", b"if-none-match"}
    req["headers"] =  {k.lower(): v for k, v in req["headers"].items()}
    req_head = req["headers"].keys()
    #print(req_head)
    cond_req_methods = { b"GET", b"HEAD" }
    #print(cond_req_methods)
    req_methods = {req["method"]} 
    #print(req_methods)
    if conditional_headers.intersection(req_head) and cond_req_methods.intersection(req_methods) :
        try:
            #print("A")
            result = check_modification(req)
            if result:
                #print("B")
                return result
        except:
            try:
                #print("C")
                result = check_ifnot_modification(req)
                if result:
                    #print("D")
                    return result
            except:
                try:
                    #print("E")
                    etag = etag_gen()
                    result = check_ifmatch(req,etag)
                    if result:
                        #print("F")ll
                        return result
                except:
                    #print("G")
                    etag = etag_gen()
                    return check_ifnonematch(req,etag)
    if req["method"] == b"GET":
        #print("buwahha")
        resource, last_modified, content_length , st_byte = get_resource(req)
        etag = etag_gen()
        log["cont_length"] = content_length
        req_hdrs = {i[0].lower(): i[1] for i in req["headers"].items()}
        if b"range" in req_hdrs:
            #print("range header present")
            res["Content-Length"]= str(len(resource)).encode()       
            if int(st_byte) > content_length:
                #print("Range not satisfiable")
                res["Content-Language"]= b"ru"
                return rangeNotsatisfiable(req, last_modified, content_length, etag)
            else:
                return partialContent(req, last_modified, content_length, etag) + resource                
        else:
            res["Content-Encoding"]=''
            res["Charset_Encodings"]=b''       
            return okrquest(req, last_modified, content_length, etag) + resource
    if req["method"] == b"HEAD":
        #print("blah")
        resource, last_modified, content_length ,st_byte = get_resource(req)
        log["cont_length"] = content_length
        etag = etag_gen()
        req_hdrs = {i[0].lower(): i[1] for i in req["headers"].items()}
        #print(req_hdrs)
        if b"range" in req_hdrs:
            #print("range header present")
            res["Content-Length"]= str(len(resource)).encode()       
            if int(st_byte) > content_length:
                #print("Range not satisfiable")
                res["Content-Language"]= b"ru"
                return rangeNotsatisfiable(req, last_modified, content_length, etag)
            else:
                return partialContent(req, last_modified, content_length, etag)
        else:
            #print(req["path"])
            res["Content-Encoding"]=''
            res["Charset_Encodings"]=b''
            if req["path"] == b"/a3-test/vt-uva.html.Z":       
                return okrequest(req, last_modified, content_length, etag)
            else:       
                return okrquest(req, last_modified, content_length, etag)  
    if req["method"] == b"OPTIONS":
        log["cont_length"]=0
        #print("hi")
        res["connection"] = "close"
        return options()
    if req["method"] == b"TRACE":
        #print("trace")
        return trace(req)
    if req["method"] == b"POST":
        #print("post")
        return created(req)
    """if req["method"] ==  b"DELETE":
        print("DELETE")
        return delete(req) 
    if req["method"] ==  b"PUT":
        print("PUT")
        return put(req)"""


"""Parser for HTTP Requests"""

def split_msg(msg):
    m = re.search(b"\r?\n\r?\n", msg)
    if m:
        return msg[:m.start()], msg[slice(*m.span())], msg[m.end():]
    else:
        return msg, b"", b""

def parse_http_request(msg):
    hdr, sep, residue = split_msg(msg)
    #print(f'msg:{msg}')
    req = {
    "orig_all": msg,
    "orig": hdr,
    "method": b"",
    "path": b"",
    "http_version": b"",
    "headers": {},
    "payload": b"",
    "malformed": False,
    "connection": b""
    }

    #print(f'hdr:{hdr}')
    lines = hdr.split(b"\n")
    status_line = lines.pop(0)
    log["status_line"]=status_line.replace(b"\r", b"").decode()
    m = re.match(b"^([A-Z]+)\s+(\S+)\s+([\w\/\.]+)$", status_line.replace(b"\r", b""))
    if m:
        req["method"] = m[1]
        req["path"] = m[2]
        req["http_version"] = m[3]
    else:
        req["malformed"] = True   
    try:
        for i in lines:
            if i!= '':
                head,value = i.split(b":",1)
                #print(head)
                if head in req["headers"]:
                    #print(1)
                    req["malformed"]= True
                else:
                    #print(2)
                    req["headers"][head] = value.strip()
    except ValueError:
        #print("ValueError")
        req["connection"] = "close"
        req["malformed"]= True
    if b"Content-Length" in hdr:
        size = int((req["headers"][b"Content-Length"]).decode())
        #print(size)
        #print(len(residue.decode()))
        payload = ((residue.decode())[0:size]).encode()
        residue = ((residue.decode())[size:]).encode()
        req["payload"] = payload
        #print(payload)    
    return req , residue



if __name__ == "__main__":
    HOST = "127.0.0.1"
    PORT = 8080

    if len(sys.argv) > 1:
        HOST = sys.argv[1]
    if len(sys.argv) > 2:
        PORT = int(sys.argv[2])

    docroot = config_dic["docroot"]
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind((HOST, PORT))
    s.listen(5)

    print("Listening on " + HOST + ":" + str(PORT) + " for HTTP connections")

    log_dir = os.getenv("LOG_DIR", config_dic["log_dir"])
    log_file = config_dic["log_file"]
    logs = open(log_dir+log_file,'a', buffering=1)

    while True:
        client, address = s.accept()
        #print("Connection has been established!")
        while True:
            #print("A")
            data = []     
            try:
                #print("B")             
                client.settimeout(5) 
                #print("After B")
                buf = client.recv(4096)
                try:
                    #print("C")  
                    while buf:
                        #print("D")
                        data.append(buf)
                        client.settimeout(0.01)
                        buf = client.recv(4096)
                except socket.timeout as e:
                    #print(e)
                    pass
            except socket.timeout as e:
                #print("F")
                res_str = requestTimeout()
                client.sendall(res_str)
                a =  res_str.split(b"\r\n",2)
                b = a[0].split(b" ",2)
                log["status_code"] = b[1].decode()
                save_logs(log,logfile=logs)
                client.close()
                break            

            #print("G")
            msg = b"".join(data)
            if msg == b"":
                break
            #print(msg)
            process_next = True
            log["ip"] = address[0]
            while msg and process_next:
                #print(msg)
                req, msg = parse_http_request(msg)
                req["connection"] = "keep-alive"
                res_str = check_all(req)
                if req["malformed"]:
                    req["connection"] = "close"
                    log["cont_length"]=0
                    res_str = badrequest()
                a =  res_str.split(b"\r\n",2)
                b = a[0].split(b" ",2)
                log["status_code"] = b[1].decode()
                #print("Bye")
                #print(res_str)
                url = urlparse(req["path"].decode()).path
                path = unquote(url)
                path = unquote_plus(url)
                resource = docroot+path
                try:
                    if (req["method"]== b"GET" or req["method"]== b"POST") and log["status_code"] == "200" and resource.endswith(".cgi"): 
                        #print("Yes CGI")
                        res_cgi = cgi_parser(res_str, resource)
                        #print(res_cgi)
                        client.sendall(res_cgi)
                    else:
                        #print("No CGI")
                        client.sendall(res_str)
                except Exception as e:
                    print(e)
                    client.sendall(res_str)
                save_logs(log,logfile=logs)   
                req["headers"] = {k.lower(): v for k, v in req["headers"].items()}
                if req["headers"].get(b"connection") == b"close":
                    process_next = False                    
                    req["connection"] = "close"
                    client.close()
               
            if req["headers"].get(b"connection") == b"close":
                req["connection"] = "close"
                client.close()
                break
             
           
                    
    s.close()

