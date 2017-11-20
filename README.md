BitStore is a DataHub microservice for storing blobs i.e. files. It is a lightweight auth wrapper for an S3-compatible object store that integrates with the rest of the DataHub stack and especially the `auth` service.

[![Build Status](https://travis-ci.org/datahq/bitstore.svg?branch=master)](https://travis-ci.org/datahq/bitstore)

## Quick Start

# Clone the repo and install

`make install`

# Run tests

`make test`

# Run server

`python server.py`

## Env Vars

* `AUTH_SERVER` - the FQ URL of the auth server. Used for looking up the public key for communicating with the auth server from the auth server.
* Object store: connection info for the underlying S3-style objectstore service
  ```
  STORAGE_ACCESS_KEY_ID
  STORAGE_SECRET_ACCESS_KEY
  STORAGE_BUCKET_NAME
  ```
* `STORAGE_PATH_PATTERN` - pattern for generating the storage path in the objectstore for a given rile. That is, `object_store_path = make_path(STORAGE_PATH_PATTERN.format{fileinfo})`. May contain any format string available for a file in authorize API including
    - `{path}` (relative path to file in package)
    - `{md5}`.
    - `{basename}` which is the filename, extracted from the `{path}`
    - `{dirname}` which is the dirname, extracted from the `{path}`
    - `{extension}` which is the extension of the filename
    - `{md5}` (and `{md5_hex}` which is the md5 in hex form)   
    Note: in addition to file info the owner and dataset (name) are available as `{owner}` and `{dataset}`.
 Examples:
  * `custom/path/{owner}/{dataset}/{path}` will, given `{owner: datahq, name: datax, path: data/file.csv}` will end up with `custom/path/datahq/datax/data/file.csv`
  * `{md5}` - storage path is md5 hash of the file (assuming md5 hash is provided)

Note: requested permissions to auth server will be like:

```
permissions:
  datapackage-upload
service:
  SERVICE_NAME (config defined above e.g. 'rawstore')
```


## API

### Get authorized upload URL(s)

`/authorize`

**Method:** `POST`

**Query Parameters:**

 - `jwt` - permission token (received from `/user/authorize`)

**Headers:**

 - `Auth-Token` - permission token (can be used instead of the `jwt` query parameter)

**Body:**

JSON content with the following structure:

```json
{
    "metadata": {
        "owner": "<user-id-of-uploader>",
        "name": "<data-set-unique-id>"
    },
    "filedata": {
        "<relative-path-to-file-in-package-1>": {
            "length": 1234, #length in bytes of data
            "md5": "<md5-hash-of-the-data>",
            "type": "<content-type-of-the-data>",
            "name": "<file-name>"
        },
        "<relative-path-to-file-in-package-2>": {
            "length": 4321,
            "md5": "<md5-hash-of-the-data>",
            "type": "<content-type-of-the-data>",
            "name": "<file-name>"
        }
        ...
    }
}
```

`owner` must match the `userid` that is in the authentication token.

**Returns**

Signed urls to upload into S3:

```javascript=
{
  fileData: {
    "<file-name-1>": {
      "md5-hash": "...",
      "name": "<file-name>",
      "type": "<file-type>",
      "upload_query": {
        'Content-MD5': '...',
        'Content-Type': '...',
        'acl': 'public-read',
        'key': '<path>',
        'policy': '...',
        'x-amz-algorithm': 'AWS4-HMAC-SHA256',
        'x-amz-credential': '...',
        'x-amz-date': '<date-time-in-ISO',
        'x-amz-signature': '...'
      },
      "upload_url": "<s3-url>"
    },
    "<file-name-2>": ...,
    ...
  }
}
```

### Get information regarding the datastore

`/info`

**Method:** `GET`

**Query Parameters:**

 - `jwt` - permission token (received from `/user/authorize`)

**Headers:**

 - `Auth-Token` - permission token (can be used instead of the `jwt` query parameter)

**Returns:**

JSON content with the following structure:
```json
{
    "prefixes": [
        "https://datastore.openspending.org/123456789",
    ]
}
```

`prefixes` is the list of possible prefixes for an uploaded file for this user.


### Check and Generate S3 Presigned URL for private objects

`/presign`

**Methos:** `GET`

**Query Parameters:**

 - `jwt` - permission token (received from `/user/authorize`)
 - `url` - original URL for S3 object
 - `ownerid` - authenticated user Id

**Headers:**

 - `Auth-Token` - permission token (can be used instead of the `jwt` query parameter)

**Returns:**

Original or Pre-Signed S3 URL:
```json
{
    "url": "https://s3.amazonaws.com/rawstore/ownername/dataset/maydata.csv?x=y",
}
```
