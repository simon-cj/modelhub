from __future__ import print_function
import subprocess
import os
import shutil
import sys
import json
import argparse
try:
    # Python 2
    from urllib import urlretrieve
    from urllib2 import urlopen, HTTPError
except ImportError:
    # Python 3
    from urllib.request import urlopen, urlretrieve
    from urllib.error import HTTPError



parser = argparse.ArgumentParser(description="Starts model with modehub framework and downloads model and prerequisites"\
                                             " if they don't exist yet."\
                                             " By default starts a webservice showing details about the model providing"\
                                             " an easy user interface to run inference.")
parser.add_argument("model", metavar = "MODEL", 
                    help = "Name of the model to run.")
parser.add_argument("-l", "--list",
                    help = "List all models available online on modelhub.",
                    action = "store_true")
parser.add_argument("-u", "--update",
                    help = "Updates MODEL to the newest version before starting it.",
                    action = "store_true")
group = parser.add_mutually_exclusive_group()
group.add_argument("-e", "--expert", 
                    help = "Start MODEL in expert mode. Provides a jupyter notebook environment to experiment.",
                    action = "store_true")
group.add_argument("-b", "--bash", 
                    help = "Start MODEL Docker in bash mode. Explore the Docker on your own.",
                    action = "store_true")



def start_basic(model_name, docker_id):
    print("")
    print("============================================================")
    print("Model started.")
    print("Open http://localhost:80/ in your web browser to access")
    print("modelhub web interface.")
    print("Press CTRL+C to quit session.")
    print("============================================================")
    print("")
    command = ("docker run --net=host -v " 
               + os.getcwd() + "/" + model_name + "/contrib_src:/contrib_src " 
               + docker_id)
    subprocess.check_call(command, shell = True)


def start_expert(model_name, docker_id):
    print("")
    print("============================================================")
    print("Modelhub Docker started in expert mode.")
    print("Open the link displayed below to show jupyter dashboard and")
    print("open sandbox.ipynb for a prepared playground.")
    print("Press CTRL+C to quit session.")
    print("============================================================")
    print("")
    command = ("docker run --net=host -v " 
               + os.getcwd() + "/" + model_name + "/contrib_src:/contrib_src " 
               + docker_id + " jupyter notebook --allow-root")
    subprocess.check_call(command, shell = True)


def start_bash(model_name, docker_id):
    print("")
    print("============================================================")
    print("Modelhub Docker started in interactive bash mode.")
    print("You can freely explore the docker here.")
    print("Press CTRL+D to quit session.")
    print("============================================================")
    print("")
    command = ("docker run -it --net=host -v " 
               + os.getcwd() + "/" + model_name + "/contrib_src:/contrib_src " 
               + docker_id + " /bin/bash")
    subprocess.check_call(command, shell = True)


def start_docker(args):
    docker_id = get_init_value(args.model, "docker_id")
    if args.expert:
        start_expert(args.model, docker_id)
    elif args.bash:
        start_bash(args.model, docker_id)
    else:
        start_basic(args.model, docker_id)


def convert_to_github_api_contents_req(url, branch_id):
    url_split = url.split("github.com")
    repo_parts = url_split[1].strip("/").split("/", 2)
    request = url_split[0] + "api.github.com/repos/" + repo_parts[0] + "/" + repo_parts[1] + "/contents"
    if len(repo_parts) == 3:
        request = request + "/" + repo_parts[2]
    request = request + "?ref=" + branch_id
    return request


def download_github_dir(src_dir_url, branch_id, dest_dir):
    request_url = convert_to_github_api_contents_req(src_dir_url, branch_id)
    response = json.loads(urlopen(request_url).read())
    if not os.path.exists(dest_dir):
        os.makedirs(dest_dir)
    for element in response:
        if element["type"] == "file":
            src_file_url = element["download_url"]
            dest_file_path = os.path.join(dest_dir, element["name"])
            print(src_file_url, "\n-->", dest_file_path)
            urlretrieve(src_file_url, dest_file_path)
        elif element["type"] == "dir":
            next_src_dir_url = src_dir_url + "/" + element["name"]
            next_dest_dir = os.path.join(dest_dir, element["name"])
            download_github_dir(next_src_dir_url, branch_id, next_dest_dir)


def download_external_files(external_files, model_dir):
    for element in external_files:
        src_file_url = element["src_url"]
        dest_file_path = os.path.join(model_dir, element["dest_file_path"].strip("/"))
        if not os.path.exists(os.path.dirname(dest_file_path)):
            os.makedirs(os.path.dirname(dest_file_path))
        print(src_file_url, "\n-->", dest_file_path)
        urlretrieve(src_file_url, dest_file_path)


def get_init_value(model_name, key):
    init_file_path = os.path.join(os.getcwd(), model_name, "init/init.json")
    with open(init_file_path) as f:
        init = json.load(f)
    return init[key]


def get_model_index():
    index_url = "https://raw.githubusercontent.com/modelhub-ai/modelhub/master/models.json"
    return json.loads(urlopen(index_url).read())


def get_model_info_from_index(model_name):
    model_index = get_model_index()
    for element in model_index:
        if element["name"] == model_name:
            return element
    raise KeyError("Model \"" + model_name + "\" not found in online model index")


def download_model(model_name, dest_dir):
    model_info = get_model_info_from_index(model_name)
    github_url = model_info["github"]
    github_branch_id = model_info["github_branch"]
    download_github_dir(github_url, github_branch_id, dest_dir)
    external_contrib_files = get_init_value(model_name, "external_contrib_files")
    download_external_files(external_contrib_files, dest_dir)


def download_model_if_necessary(args):
    model_dir = os.path.join(os.getcwd(), args.model)
    if args.update and os.path.exists(model_dir):
        print("Removing existing model ...")
        shutil.rmtree(model_dir)
    if os.path.exists(model_dir):
        print("Model folder exists already. Skipping download.")
    else:
        print("Downloading model ...")
        download_model(args.model, model_dir)
        print("Model download DONE!")



def start(args):
    download_model_if_necessary(args)
    start_docker(args)


def list_online_models():
    model_index = get_model_index()
    model_names = [element["name"] for element in model_index]
    descriptions = [element["task_extended"] for element in model_index]
    header1 = "Model"
    header2 = "Description"
    sep1_length = max(len(max(model_names, key=len)), len(header1))
    sep2_length = max(len(max(descriptions, key=len)), len(header2))
    print(header1 + " "*(sep1_length - len(header1)) + "  " + header2)
    print("-"*sep1_length + "  " + "-"*sep2_length)
    for i in range(len(model_names)):
        print(model_names[i] + " "*(sep1_length - len(model_names[i])) + "  " + descriptions[i])



if __name__ == "__main__":
    try:
        # The extra manual parsing of the "--list" parameter is temporary until
        # we have modelhub in a pip installable package and an extra list
        # command. argparse does not support optional mandatory positional args
        # based on the presence of certain flags (i.e. we don't want to require
        # a MODEL when "--list" is given, but otherwise we do!)
        if "-l" in sys.argv[1:] or "--list" in sys.argv[1:]:
            list_online_models()
            sys.exit(0)
        else:
            args = parser.parse_args()
    except SystemExit as e: 
        if e.code == 2:
            parser.print_help()
        sys.exit(e.code)
    try:
        start(args)
    except HTTPError as e:
        print("ERROR: Model download failed. Please check if this is a valid model name. Also, please check your internet connection. The model folder \"" + args.model + "\" is possibly corrupt. Please delete it (if it exists).")
        print("ERROR DETAIL: ", e)
        if e.code == 403:
            print("An HTTP 403 error usually means that GitHub rejected our request. The reason is that GitHub limits the number of anonymous requests from a certain IP address per hour. This unfortunately means that you will have to wait about an hour until you can download more models. You can still run all your local models, of course.")


