### 

Details

Subscription

d778faac-02a4-4d74-9881-199994f2bd98

Resource Group

HWB-SIGMAJAN-PROD

Name

SIGMAJAN-APP

Secure unique default hostname

Enabled

Publish

Code

Runtime stack

Python 3.12

### 

App Service Plan (New)

Name

ASP-HWBSIGMAJANPROD-b39c

Operating System

Linux

Region

Central US

SKU

Basic

Size

Small

ACU

100 total ACU

Memory

1.75 GB memory

### 

Database (New)

Username and password of the new database are generated automatically. To retrieve these values after the deployment, go to the App Settings of your app.

Server name

sigmajan-server

Engine

PostgreSQL - Flexible Server

Compute tier and size

Burstable Standard_B1ms

Database name

sigmajan-adb

Region

Central US

Username

kpbxmfusni

Password

****************

### 

Networking

Virtual Network

(New) SIGMAJAN-APPVnet (10.0.0.0/16)

Inbound subnet

(New) SIGMAJAN-APPSubnet (10.0.0.0/24)

DNS

Azure Private DNS Zone

Outbound subnet (Web App)

(New) SIGMAJAN-APPAppSubnet (10.0.1.0/24)

Outbound subnet (Database)

(New) SIGMAJAN-APPDbSubnet (10.0.2.0/24)