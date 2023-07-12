# Zephyr/1.0

Zephyr is an AI-driven data science service.



# How to deploy and run in Azure

This will set up and configure a complete environment in your Azure subscription. The far easiest way is to use a GitHub codespace (you must install the az cli) or the Azure Cloud Shell (you must then git clone this repo).

```
  # install azure cli tools
  # curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash

  # login with az login
  # az login

  # if more than one subscription, set your preferred one
  # az account set -n <name_or_id>

  # then...
  cd ./deploy
  ./deploy
```

Note! configuration.toml will contain secrets; ensure you do not commit this file and remove it safely (it is needed for debugging, pushing updates, etc while in development so keep your dev and prod environments separate).

After making changes to the server or worker, push the latest version to cloud by:

```
  cd ./deploy
  pip install -r requirements.txt
  ./push
```



# How to run the (web) server locally

The server handles ui and user interactions. It contains both the api
and the frontend and uses Flask and Ninja templates (see static and templates folders).

1. Deploy to Azure (see above, you need the storage account)
1. You have two options, direct or via docker (preferred)

## Run with docker

```
  cd ./deploy
  . ./setenv

  cd ../server
  ./runlocal.sh
```

## Run directly with Python

```
  cd ./deploy
  . ./setenv

  cd ../server
  pip install -r requirements.txt
  python3 server.py
```



# How to run the worker locally

The worker processes datasets after they are uploaded to an azure blob. The upload triggers and event grid notification that posts a message to the "ingestion" queue in the storage account, which is consumed by the worker(s).

To run the worker locally, you must first delete the worker in azure, otherwise they will compete to get new messages. You can redeploy the worker by copying the deployment code from the ./deploy/deploy script. Look for the `az containerapp create` commands.

1. Deploy to Azure (see above, you need the storage account)
1. Delete the worker in Azure
1. You have two options, direct or via docker (preferred)

## Run with docker

```
  cd ./deploy
  . ./setenv

  cd ../workers/ingestion
  ./runlocal.sh
```

## Run directly with Python

```
  cd ./deploy
  . ./setenv

  cd ../workers/ingestion
  pip install -r requirements.txt
  
  python3 worker.py
```


# How to run the scripthost locally

The scripthost will execute python scripts created by GPT to analyse a dataset, by first downloading the dataset and making it available to the script.

It is recommended that you run the scripthost in isolation through docker, and not directly on your own machine with unknown scripts (although you can in the same way as the ingestion worker).

To run the worker locally, you must first delete the worker in azure, otherwise they will compete to get new messages. You can redeploy the worker by copying the deployment code from the ./deploy/deploy script. Look for the `az containerapp create` commands.

1. Deploy to Azure (see above, you need the storage account)
1. Delete the worker in Azure
1. You have two options, direct or via docker (preferred)

## Run with docker

```
  cd ./deploy
  . ./setenv

  cd ../workers/scripthost
  ./runlocal.sh
```



# How to contribute

Fork and open a PR!



# Todo list

- [x] Create a scaffold for this stuff
- [x] Deployment to Azure
- [ ] Smooth local development and debugging
- [ ] Deploy a log analytics workspace and config containers to write logs there
- [ ] Set filename header when downloading report
