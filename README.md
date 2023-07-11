# Zephyr/1.0

Description of this stuff here for people finding us on GitHub or wanting to contribute.



# How to run

Preferred, requires docker:

```
  cd ./server && runlocal.sh
```

Direct:

```
  cd ./server && pip install -r requirements.txt && python3 server.py
```


# How to deploy

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


# How to contribute

Fork and open a PR!



# Todo list

- [ ] Create a scaffold for this stuff



# Stuff to get this running

```
az extension add --name containerapp --upgrade
az provider register --namespace Microsoft.App
az provider register --namespace Microsoft.OperationalInsights

az deployment group create --resource-group Zephyr-0.1 --template-file queue.json --parameters environment_name=vkrjjzaur queueconnection=$qcs location=swedencentral

```
