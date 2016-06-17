---
layout: post
title: Database Mappings
date: 2016-06-16T17:58:19.000Z
categories:
  - Database
weather:
- temp: 97
- cond: day-sunny
---
**Problem**

You are starting work on a website that is database driven. Before now there has only been one developer who has been developing in the QA instance of the website. Since there are now two of you he has decided to create two development instances of the website for you both to work on and not interfere with each other's work. When you log into the development instance you find that there is no data loaded into the instance. You inquire and the site is managed by a third party and exporting the data to the development instance would cost additional money. You decide to simply export from the QA instance and import into the development instance. You are concerned about three tables: `accounts`, `customers`, and `issues`. When you try to import these three tables you find the import process is not preforming the lookup correctly. You need to find a way to correctly map the tables together as efficiently as possible.
