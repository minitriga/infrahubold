---
label: GraphQL Mutation
# icon: file-directory
tags: [tutorial]
order: 100
---

GraphQL Mutations are available to create, update or delete any objects in the database. In a REST API they are the equivalent of a the methods POST, PUT or DELETE.

```graphql # Create a new organization
# Endpoint : http://localhost:8000/graphql/main
mutation {
  organization_create(
    data: {
      name: { value: "Hooli" },
      description: { value: "Transforming the world as we know it."}
    }
  ) {
    ok
    object {
      id
    }
  }
}
```



### Add a new interface and a new IP address in the Graph

Add a new interface `Ethernet9` to the device `ord1-edge1`
```graphql
# Endpoint : http://127.0.0.1:8000/graphql/cr1234
mutation {
  interface_l3_create(
    data: {
      name: { value: "Ethernet9" }
      enabled: { value: true }
      description: { value: "new interface in branch" }
      device: { id: "ord1-edge1" }
      status: { id: "active" }
      speed: { value: 10000 }
      role: { id: "spare" }
    }
  ) {
    ok
    object {
      id
      name {
        value
      }
      description {
        value
      }
    }
  }
}
```
> Copy the ID of the newly created interface, we'll need it for the next query

Add a new IP address connected to the new interface

```graphql
# Endpoint : http://127.0.0.1:8000/graphql/cr1234
mutation {
  ipaddress_create(
    data: {
      interface: { id: "<INTERFACE Ethernet9 UUID>" },
      address: { value: "192.168.0.2/24" }
    }
  ) {
    ok
    object {
      id
      address {
        value
      }
    }
  }
}
```