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
