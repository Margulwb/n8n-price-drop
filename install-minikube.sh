#!/bin/bash

set -e

sudo dnf update -y
sudo dnf install -y yum-utils curl conntrack

sudo yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
sudo dnf install -y docker-ce docker-ce-cli containerd.io

sudo systemctl enable --now docker
sudo usermod -aG docker $USER

K8S_VERSION=$(curl -L -s https://dl.k8s.io/release/stable.txt)
curl -LO "https://dl.k8s.io/release/${K8S_VERSION}/bin/linux/amd64/kubectl"
sudo install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl
rm kubectl

curl -LO https://storage.googleapis.com/minikube/releases/latest/minikube-linux-amd64
sudo install minikube-linux-amd64 /usr/local/bin/minikube
rm minikube-linux-amd64

minikube start --driver=docker
minikube status
kubectl get nodes
minikube ssh "sudo mkdir -p /var/log/price-drop /opt/price-drop && sudo chown 1000:1000 /var/log/price-drop /opt/price-drop"