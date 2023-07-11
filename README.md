# Zephyr/1.0

Zephyr is an AI-driven data science service.



# How to deploy and run in Azure

This will set up and configure a complete environment in your Azure subscription.

```
  # install azure cli tools
  # curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash
  # login with az login and set your preferred subscription with az account set
  # then...
  cd ./deploy
  pip install -r requirements.txt
  ./deploy
```

Note! configuration.toml will contain secrets; ensure you do not commit this file and remove it safely (it is needed for debugging, pushing updates, etc while in development so keep your dev and prod environments separate).

After making changes to the server or worker, push the latest version to cloud by:

```
  cd ./deploy
  ./push
```



# How to run the (web) server locally

The server handles ui and user interactions. It contains both the api
and the frontend and uses Flask and Ninja templates (see static and templates folders).

1. Deploy to Azure (see above, you need the storage account)
1. You have two options, direct or via docker (preferred)

## Run with docker

```
  cd ./server
  . ../deploy/setenv
  ./runlocal.sh
```

## Run directly with Python

```
  cd ./server
  pip install -r requirements.txt
  ../deploy/setenv
  python3 server.py
```



# How to run the worker locally

The worker processes datasets after they are uploaded to an azure blob. The upload triggers and event grid notification that posts a message to the "ingestion" queue in the storage account, which is consumed by the worker(s).

To run the worker locally, you must first delete the worker in azure, otherwise they will compete to get new messages. You can redeploy the worker by copying the deployment code from the ./deploy/deploy script.

1. Deploy to Azure (see above, you need the storage account)
1. Delete the worker in Azure
1. You have two options, direct or via docker (preferred)

## Run with docker

```
  cd ./worker
  . ../deploy/setenv
  ./runlocal.sh
```

## Run directly with Python

```
  cd ./worker
  pip install -r requirements.txt
  ../deploy/setenv
  python3 worker.py
```


# How to contribute

Fork and open a PR!



# Todo list

- [x] Create a scaffold for this stuff
- [x] Deployment to Azure
- [ ] Smooth local development and debugging
- [ ] Deploy a log analytics workspace and config containers to write logs there
