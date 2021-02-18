# URL MONITOR

Small utility to monitor the availability of websites.

The utility consists of two components; a monitor and a writer.
The monitor checks the website's availability and produces a Kafka message with the results.
The writer consumes said message and persists it to a database.

## Deployment
The application is deployed and run as two docker containers, one per component.
The containers and the backing Kafka broker and database are automatically deployed via Terraform.

To deploy the application run:

```
$ terraform apply
```

The `targets` input variable needs to be defined.

## Testing
### Unit tests
Unit tests are run automatically during the creation of the docker image.
They can however, be run manually by running `tox` on the repository root.
Alternatively, they can also be run with `pytest` assuming that the utility's dependencies are installed.

### Integration tests
Integration tests are automated with Terraform and can be run as follows:

```
$ terraform apply -var="integration=true"
```
