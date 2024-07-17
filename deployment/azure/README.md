# Deploy to Azure

## Overview

We deploy the frontend on Storage Account's Static Web Hosting and it gets a HTTPS link. MS AAD (for authentication) cannot be deployed on a HTTP link. 

We deploy the API Server and Engine as containers. API should be publicly accessible with a HTTPS link. For this we use a App Gateway.

We need to create SSL cert for the App Gateway to ensure that both frontend and server are on a HTTPS link. We typically store the SSL certs in KeyVault. For other resources to access the KeyVault we need Managed Identities.

We use Event Hub (kafka equivalent) and Postgres Flexible Server 

## Deployment of the Frontend

Generate a build of the frontend using the right env variables

```bash
VITE_REACT_APP_AAD_APP_CLIENT_ID="" \
VITE_REACT_APP_AAD_APP_TENANT_ID="" \
VITE_REACT_APP_AAD_APP_REDIRECT_URI="https://${APP_DOMAIN}/" \
VITE_REACT_APP_AAD_APP_SCOPE_URI="" \
VITE_REACT_APP_SERVER_HOST="https://${API_DOMAIN}" \
VITE_REACT_EDITOR=code \
npm run build
```

Publish it to Storage Account

```bash
az storage blob upload-batch -s ./dist -d \$web --account-name STORAGE_ACCOUNT_NAME --overwrite
```

## Deploying the containers

Suitably update the `parameters.json` for server and engine.

```bash
 az deployment group create --resource-group RG_NAME --template-file template.json --parameters @parameters.json
```

## Generation of SSL certs 

After install `certbot` you can generate a free SSL certificate from your local machine

We need a SSL certificate for api server

```bash
export DOMAIN=api.domain.com
sudo certbot certonly --manual --preferred-challenges dns -d $DOMAIN
```

You will need to add the `TXT` record to your Domain. Check instructions with provider

```bash
sudo openssl pkcs12 -export -out ${DOMAIN}.pfx -inkey /etc/letsencrypt/live/$DOMAIN/privkey.pem -in /etc/letsencrypt/live/$DOMAIN/fullchain.pem
```

We need to do a simliar one for static website for the studio interface. Run the above commands by changing the value of $DOMAIN 
