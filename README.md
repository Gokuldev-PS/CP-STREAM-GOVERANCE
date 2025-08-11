# CP-DataQualityRulesDemo

This repository showcases a demo of **data quality rules** on the **Confluent Platform**.

## 🚀 Step 1: Deploy Confluent Platform

First, deploy the Confluent Platform cluster on Kubernetes.  
You can use an existing instance or a managed Kubernetes service like **AKS**, **EKS**, etc.

### 🔐 License Setup

If you don’t have a Confluent license, you can remove the following section from your Confluent Platform (CP) config:

```yaml
spec:
  license:
    secretRef: confluent-license
```


Then create a Kubernetes secret using the following command:

```yaml
kubectl create secret generic confluent-license \
  --from-file=license.txt=./license.txt \
  --namespace confluent
```


### 🛠️ Install Confluent Operator

Add the Helm repo and install the Confluent Operator:

```bash
helm repo add confluentinc https://packages.confluent.io/helm
helm repo update

helm upgrade --install confluent-operator \
  confluentinc/confluent-for-kubernetes \
  --namespace confluent

```

Apply the Confluent Platform configuration:

```bash
cd CP
kubectl apply -f cp.yaml
```
Check the status of pods:
```bash
kubectl get pods -n confluent
```
Retrieve LoadBalancer endpoints:
```bash
kubectl get services -n confluent
```
You will need the endpoints for:
1)Kafka Bootstrap
2)REST Proxy
3)Schema Registry

<image src >


---

##  Step 2: Create Topics and Schemas

Navigate back to the root directory:

```bash
cd ..
