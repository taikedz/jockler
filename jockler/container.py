import common
import run
import image
import store
import options
import re
import time
import sys
import os

# jockler start {new|last|stable} IMAGE [ATTACH]

def start(args):
    if len(args) >= 2:
        instance = args[0]
        imagename = args[1]

        doattach = common.item(args, 2, False)
        if doattach == "attach":
            doattach=True

        if not instance in ["new", "last", "stable"]:
            common.fail("Incorrect instance name. Please use 'new', 'last', or 'stable' ")

        if instance == "new":
            containername = start_new_container(imagename, doattach)
        else:
            containername = store.read_data(instance, imagename)
            if containername:
                start_container(imagename, containername, doattach)
            else:
                common.fail("No instance %s for image %s"%(instance, imagename))

    elif len(args) == 1:
        containername = args[0]
        imagename = extract_image_name(containername)
        if imagename:
            start_container(imagename, containername)
    
    else:
        common.fail("Unknown. Use 'jockler start {new|last|stable} IMAGE' or 'jockler start CONTAINER'")

def stop(args):
    if not common.args_check(args, 1):
        common.fail("Unknown sequence for stop: %s" % ' '.join(args))

    imagename = args[0]
    forcemode = False
    if imagename == "-f" and common.item(args, 1, None) != None:
        forcemode = True

    if forcemode:
        for containername in args[1:]:
            force_stop(containername)
    else:
        stop_containers(imagename)

def extract_image_name(containername):
    m = re.match("^(jcl|dcv)_("+common.imagenamepat+")_[0-9]+$", containername)
    if m:
        return m.group(2)
    common.fail("[%s] is not a container managed by jockler" % containername)

def get_running_containers(imagename):
    code, sout,serr = run.call(["docker","ps", "--format", "{{.Names}}", "--filter", "name=jcl_%s_"%imagename], silent=True)

    containernames = sout.strip().split("\n")
    common.remove_empty_strings(containernames)
    return containernames

def stop_containers(imagename):
    containernames = get_running_containers(imagename)

    if len(containernames) > 0:
        code, sout, serr = run.call( ["docker", "stop"] + containernames )
        if code > 0:
            common.fail("Error stopping container(s) !\n%s"%(sout))

        code, sout, serr = run.call( ["docker", "update", "--restart=no"] + containernames )

def force_stop(containername):
    res,sout,serr = run.call(["docker", "update", "--restart=no", containername])
    if res > 0:
        common.fail("Could not update restart policy on container [%s]"%containername)

    res,sout,serr = run.call(["docker", "stop", containername])

def found_running_container(containername):
    time.sleep(1)
    code, sout, serr = run.call(["docker", "ps", "--format", "{{.Names}}", "--filter", "name=%s"%containername], silent=True)
    containers = sout.strip().split(os.linesep)
    return containername in containers

def load_container_options(imagename):
    coptions = options.read_options(imagename)
    if coptions == None:
        coptions = []
    return coptions

def generate_container_name(imagename):
    datime = common.timestring()
    return "jcl_%s_%s" % (imagename, datime)

def start_container(imagename, containername, doattach=False):
    stop_containers(imagename)
    store.write_data("last", imagename, containername)

    runmode = []
    useexec = False
    if doattach:
        runmode.append("-i")
        useexec = True

    print("Starting %s"%containername)

    code, sout, serr = run.call( ["docker", "start", containername]+runmode, stdout=sys.stdout, stderr=sys.stderr, useexec=useexec )

    if code > 0 or not found_running_container(containername):
        common.fail("Could not start container %s - try starting with 'attach' mode'\n%s"%(containername,sout))

    code, sout, serr = run.call( ["docker", "update", "--restart=unless-stopped", containername])

def start_new_container(imagename, doattach=False):
    stop_containers(imagename)
    containername = generate_container_name(imagename)
    options = load_container_options(imagename)

    runmode = "-d"
    useexec = False
    if doattach:
        runmode = "-it"
        useexec = True

    code, sout, serr = run.call(["docker", "run", runmode, "--name=%s"%containername]+options+[imagename], useexec=useexec)

    if code > 0 or not found_running_container(containername):
        common.fail("Could not create new container for %s, or could not start created container:\n%s"%(imagename, sout))

    # Do not do this on initial docker-run - otherwise, if the entrypoint is faulty
    #   you get continually restarting containers that are hard to stop
    code, sout, serr = run.call( ["docker", "update", "--restart=unless-stopped", containername])

    store.write_data("last", imagename, containername)

    return containername
