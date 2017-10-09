# Dockervisor

A tool for managing Docker images, containers, and rollback.

## Features

* start/stop latest container using the image name - let dockervisor manage container instances
* mark specific container as "stable" - rollback to a "stable" version after running a new container, if needed
* ensure every container for a given image uses the same data volumes
* backup and restore volume data (Linux only for now) across hosts
* automatically clean out old, unused containers and images

Dockervisor allows you to start and stop containers by specifying the image name, instead of individual container names. Any one image managed by dockervisor can only have one container running.

Dockervisor ensures that all containers started by dockervisor use the same port exposures and volume mounts, using a `dcv-$IMAGENAME` file.

This means that if you build a new version of an image, your new container will use the same data as the old container.

## Pre-requisites

* Dockervisor is implemented in Python 3
* You will need the latest docker-ce: see the [official docker documentation](https://www.docker.com/community-edition)

Install the Dockervisor tool:

	git clone https://github.com/taikedz/dockervisor
	sudo dockervisor/install.sh

	# Optionally, enable autostart
	sudo systemctl enable dockervisor-autostart

## Quickstart

In a directory with a Dockerfile, build the image, and register its port exposures and volume mounts. If the image already existed, it is replaced with a newer version.

	dockervisor build IMAGENAME .

Start a fresh container from the image - this always creates a new container and starts it, even if others had previously been created. Port exposures and volume mounts are pulled from dockervisor store `/var/dockervisor` on Linux, `%HOME%/dcv-data` on Windows.

	dockervisor start new IMAGENAME

Stop the container

	dockervisor stop IMAGENAME

Start the last used container from that image

	dockervisor start last IMAGENAME

Mark the currently running container as stable - one you might want to come back to after upgrading an image

	dockervisor stable IMAGENAME

Start the last known stable container

	dockervisor start stable IMAGENAME

List images (present and past) associated with IMAGENAME

	dockervisor list images IMAGENAME

Backup your data

	dockervisor volumes backup linux IMAGENAME

Restore your data

	dockervisor volumes restore linux IMAGENAME ARCHIVEFILE

## Usage

### Creating a new image and container

Switch in to the folder with your Dockerfile, and use dockervisor to build a new image:

	dockervisor build IMAGENAME .
	dockervisor start new IMAGENAME

This builds a fresh image to be called `IMAGENAME`, and runs a container based off of it.

You can subsequently run the `dockervisor` command from anywhere to stop/start a container if its image has already been built once.

### Stopping and starting the container

Stop the existing container by image name:

	dockervisor stop IMAGENAME

Start the container again:

	dockervisor start last IMAGENAME

Start a container by name - the container must be of the format `dcv_$IMAGENAME_$SUFFIX`:

	dockervisor start container_name

### Marking stable

You can mark the currently running container as "stable", to indicate that it should be the fallback version

	dockervisor stable mark IMAGENAME

You can start the registered stable container by running

	dockervisor start stable IMAGENAME

You can see which container is marked as stable

	dockervisor stable show IMAGENAME

The `stable` label always points to the same container until explicitly changed.

### Updating the image and container

Simply run the build command against the image name

	dockervisor build IMAGENAME .

Running `last` will still run the previously existing container, we must create a new container which becomes the new last.

	dockervisor start new IMAGENAME

### Rollback

Run your stable version - this will also stop any currently running version.

	dockervisor start stable IMAGENAME

### Auto-start

Dockervisor can mark images for automatic starting:

	dockervisor autostart IMAGENAME {last|stable|none}

If not set, or set to none, the image's container will not be started

To run all containers marked for autostart, run

	dockervisor start-all

To have this run at host startup, run

	systemctl enable dockervisor-autostart

This is only available on systems with systemd.

### Backup and restore

You can create .TAR.GZ backup files of a `last` container of an image

	dockervisor volumes backup linux IMAGENAME
	dockervisor volumes restore linux IMAGENAME ARCHIVENAME

You need to specify `linux` for Linux-based containers ; support for Windows-based containers will eventually be added.

Before restoring, you need an initial container - if you are moving to another host, using the same dockerfile and optional remapping file, you can execute the following sequence:

	dockervisor build IMAGENAME DIRECTORY
	dockervisor start new IMAGENAME
	dockervisor stop IMAGENAME
	dockervisor volumes restore linux IMAGENAME ARCHIVENAME
	dockervisor start last IMAGENAME

### Deletion

You can have dockervisor remove all containers and images associated with an image name with these commands:

	dockervisor cleanup IMAGENAME
	dockervisor remove IMAGENAME

The `cleanup` operation does not remove the last container run, and does not remove the `stable` container; it also does not remove the images associated with these. All other containers and images associated with this image name are removed.

The `remove` operation removes ALL containers and images associated with this image name.

Both prompt you once before execution.

## Implementation specifics

### Images

The name of the image determines a family of containers. Different images can be created from a same Dockerfile ; as such two apache images could be created from a same Dockerfile and have a separate family of containers each.

This does create image duplication, however it eases container management separation.

Images rebuilt with the same name leave their old image behind as an unnamed image for the original containers to continue using.

You can use `dockervisor list images IMAGENAME` to list all images associated with that name.

### Containers

Containers get named as `dcv_$IMAGENAME_$DATE` upon creation.

Dockervisor keeps track of which was last run, and which is marked as stable.

### Volumes

Dockervisor uses the `VOLUME` directives from the Dockerfile to generate volumes based on image name and path, unless overridden (see Remapping section).

Every time a new container is created from a same image, it inherits the same volumes as its predecessor, since the volume name is generated deterministically.

For example, for an image created as `mainapache` and exposing a mount location of `/var/www`, a volume called `dcv_mainapache_var_www` is created. Any container created from the `mainapache` image will receive the same named volume.

### Ports

Dockervisor uses the `EXPORT` directives from the Dockerfile to generate port exposure mappings, unless overridden (see Remapping section).

Ports get mapped out one-to-one by default - for example, if the Dockerfile specifies `EXPOSE 8080`, then a mapping `-p 8080:8080` is used.

## Remapping

A remapping overrides file can be specified to override the ports: add a `dcv-$IMAGENAME` to the same directory as the Dockerfile containing a JSON data file with the appropriate keys.

Multiple keys can be used (once per key name) in the same overrides file.

### Ports

Use a "ports" key using a map of `host port --> container port definition`

for example, to expose the container's port `8080` on the host's port `80`, and the container's port `22` on the host's port `8022`

	{
		"ports": {
			"80":"8080/tcp",
			"8022":"22"
		}
	}

You can optionally specify the transport `/tcp` or `/udp` after the container port.

### Volumes

Use a "volumes" key using a map of `host path or volume --> container mount point`

for example, to mount `my_custom_volume` on `/var/data`:

	{
		"volumes": {
			"my_custom_volume":"/var/data"
		}
	}

The host portion can be a directory, or a docker volume
