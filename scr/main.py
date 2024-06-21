import requests, json, re, os, time
from tqdm import tqdm
from requests_toolbelt.multipart.encoder import MultipartEncoder, MultipartEncoderMonitor
from pathlib import Path
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

def requests_retry_session(
    retries=3,
    backoff_factor=0.3,
    status_forcelist=(500, 502, 504),
    session=None,
):
    session = session or requests.Session()
    retry = Retry(
        total=retries,
        read=retries,
        connect=retries,
        backoff_factor=backoff_factor,
        status_forcelist=status_forcelist,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session
    
def natural_keys(text):
    return [ (int(c) if text.isdigit() else text) for c in re.split(r'(\d+)', text) ]

def uploadfile(file:str):
    print(f'{os.path.basename(file)} is Uploading now.')
    start_time = time.time()

    def callback(monitor):
        elapsed_time = time.time() - start_time
        speed = monitor.bytes_read / elapsed_time / (1024 * 1024)

        if speed > 0:
            remaining_time = (monitor.len - monitor.bytes_read) / (speed * 1024 * 1024)
            eta=f"{remaining_time:.2f} seconds"
        else:
            eta='♾️ seconds'

        pbar.set_postfix({"Speed": f"{speed:.2f} MB/s", "ETA": eta})
        progress = (monitor.bytes_read / monitor.len) * 100
        pbar.update(round(progress, 2) - pbar.n)

    multipart_data = MultipartEncoder(
        fields={
            'files[]': (Path(file).name, open(file, 'rb'), 'text/plain')
        }
    )

    pbar = tqdm(total=100, desc="Upload Progress", unit="%", bar_format='{desc}: {percentage:3.0f}%|{bar}| {n_fmt}/{total_fmt}{postfix}')
    try:
        response = requests_retry_session(retries=20, backoff_factor=60).post('https://up1.fileditch.com/upload.php', data=MultipartEncoderMonitor(multipart_data, callback), headers={'Content-Type': multipart_data.content_type})
    except Exception as x:
        print('It failed :', x.__class__.__name__)
    pbar.set_postfix(eta="Almost there...")
    
    if response.status_code == 200:
        pbar.set_postfix(eta="Done")
        pbar.close()
        print(f"File uploaded successfully!\n")
        return json.loads(response.text)["files"][0]["url"]
    else:
        pbar.set_postfix(eta="Error")
        pbar.close()
        print(f"Failed to upload. Status code: {response.status_code}")
        
def sendmessage(message:str, url, name=None, thread_id=None):
    payload = {"content": message}
    if name: payload["thread_name"]=name
    response = requests.post(f'{url}?thread_id={thread_id}' if thread_id else url, json=payload)

    if response.status_code == 204:
        print(f"Message sent successfully!\n")
    elif response.status_code == 429:
        wait = json.loads(response.text)["retry_after"]
        print(f'You have been rate limited by discord. Retrying in {wait}')
        time.sleep(wait)
        sendmessage(message, url, name, thread_id)
    else:
        print(f"Failed to send message. Status code: {response.status_code}\n")

def make_embed(video, image):
    data = {
        'video': video,
        'image': image
    }

    response = requests.post('https://discord.nfp.is/', data=data)
    if response.status_code == 200:
        if response.url == 'https://discord.nfp.is/':
            print('You have been rate limited by discord.nfp.is links will no longer be shortened.')
            return f'https://discord.nfp.is/?v={video}&i={image}'
        else:
            return response.url
    else:
        print(f"Failed to Make Embed. Status code: {response.status_code}")

def option(list):
    choices = [str(i) for i in range(1, len(list)+1)]
    print(f"Choose a option:  ")
    for i in range(len(list)):
        print(f"{i+1}. {list[i]}")
    while True:
        choice = input(f"Option:  ")
        print("")
        if choice in choices:
            choice = int(choice)
            break
        else:
            print(f'\nInvalid choice. Please choose again.')
    return choice

def get_path():
    while True:
        file_path = input("Path:  ").replace('"', "")
        if file_path.startswith('& '): file_path = file_path[2:]

        if os.path.exists(file_path):
            return file_path
        else:
            print(f"Invalid path.\n")

def get_file_path():
    while True:
        path = get_path()
        if os.path.isfile(path):
            return path
        else:
            print(f"Invalid path (File Path Not Folder).\n")

def get_txt_path():
    while True:
        allowed_formats = ['.txt']
        
        path = get_file_path()
        _, file_extension = os.path.splitext(path)

        if file_extension.lower() in allowed_formats:
            return path
        else:
            print("The file is not a .txt file.")

def get_webhook_url():
    while True:
        webhook_url = input('Webhook URL:  ')

        if not webhook_url.startswith("https://discord.com/api/webhooks"):
            print("Webhook link has to be Discord.")
        else:
            try:
                response = requests.get(webhook_url)
                if response.status_code == 200:
                    break
                else:
                    print("Incorrect Webhook link/Webook Does Not Exist.")
            except requests.exceptions.RequestException:
                print("Incorrect Webhook link/Webook Does Not Exist.")
    thread_or_fourm = option([
#        "Forum Channel? (Will make a channel with the name provided.)",
        "Thread? (Will ask for Thread ID.)",
        "None of the above."
    ])
    Fourm_Name=None
    Thread_ID=None
    match thread_or_fourm:
        case 1:
#            Fourm_Name = input("Forum Name:  ")
#        case 2:
            Thread_ID = input("Thread ID:  ")
    return webhook_url, Fourm_Name, Thread_ID

def upload(movie_or_series, embed, send_to_discord):
    # Start
    folder_or_path = option([
        f"Pull files from ./Upload{movie_or_series_list[movie_or_series-1]}",
        "Pull from path"
    ])
    folder = False   
    match folder_or_path:
        case 1:
            folder = True
            if DEFAULT_DIR_TOGGLE:
                path = get_path()
            else:
                if movie_or_series == 1:
                    path = './UploadMovie/'
                elif movie_or_series == 2:
                    path = './UploadSeries/'
                    
            os.makedirs(path, exist_ok=True)

            if len(os.listdir(path)) == 0:
                print(f"Folder is empty. Please place files in the folder.\n")
                raise _Menu()

        case 2: 
            folder = False

    while True:
        if not ((folder) and (movie_or_series == 1)):
            if embed:
                image = input('Thumbnail URL:  ')
            name = input(f'{movie_or_series_list[movie_or_series-1]} name:  ')
            hs = open(f"{name}.txt","a")

        if send_to_discord:
            webhook_url, Fourm_Name, Thread_ID = get_webhook_url()

        match movie_or_series:
            case 1:
                # Start
                if folder:
                    alist=os.listdir(path)
                    alist.sort(key=natural_keys)
                    for file in alist:
                        if embed:
                            image = input('Thumbnail URL:  ')
                        name = input(f'Movie name:  ')
                        hs = open(f"{name}.txt","a")

                        fileurl = uploadfile(os.path.join(path, file))

                        if embed:
                            message = f'[{name}]({make_embed(fileurl, image)})\n'
                        else:
                            message = f'{fileurl}\n'
                        hs.write(message)
                        if send_to_discord:
                            sendmessage(message, webhook_url, Fourm_Name, Thread_ID)

                        hs.close()
                else:
                    path = get_file_path()
                    fileurl = uploadfile(path)

                    if embed:
                        message = f'[{name}]({make_embed(fileurl, image)})\n'
                    else:
                        message = f'{fileurl}\n'
                    hs.write(message)
                    if send_to_discord:
                        sendmessage(message, webhook_url, Fourm_Name, Thread_ID)

                hs.close()
                # End

            case 2:
                # Start
                i = 0
                if folder:
                    # Start
                    alist=os.listdir(path)
                    alist.sort(key=natural_keys)
                    for file in alist:
                        i+=1
                        fileurl = uploadfile(os.path.join(path, file))
                        if embed:
                            message = f'[{name} - Episode {i}]({make_embed(fileurl, image)})\n'
                        else:
                            message = f'{fileurl}\n'
                        hs.write(message)
                        if send_to_discord:
                            sendmessage(message, webhook_url, Fourm_Name, Thread_ID)
                    # End
                else:
                    # Start
                    while True:
                        try:
                            num = int(input('How Many Episodes:  '))
                            break
                        except ValueError:
                            print("Please enter a valid integer.") 

                    for i in range(num):
                        i+=1

                        path = get_file_path()
                        
                        fileurl = uploadfile(path)
                        if embed:
                            message = f'[{name} - Episode {i}]({make_embed(fileurl, image)})\n'
                        else:
                            message = f'{fileurl}\n'
                        hs.write(message)
                        if send_to_discord:
                            sendmessage(message, webhook_url, Fourm_Name, Thread_ID)
                    # End
                # End

        hs.close()

        print(f"\nWould You Like To Do Another {movie_or_series_list[movie_or_series-1]}?")
        if option(["Yes", "No"]) == 2:
            break
    # End

class _Menu(Exception): pass

DEFAULT_DIR_TOGGLE = False

movie_or_series_list = [
    "Movie", 
    "Series"
]

def main():
    choice = option([
        "Upload a movie/series and send to discord", 
        "Upload and make embed (Doesn't send on discord)",
        "Upload Only",  
        "Links to embed", 
        "Send txt to Discord",
        "Exit"
    ]) 

    if choice not in [5, 6]:
        movie_or_series = option(movie_or_series_list) 
    try:
        match choice:
            case 1 | 2 | 3:
                # Start
                match choice:
                    case 1:
                        upload(movie_or_series, True, True)
                    case 2:
                        upload(movie_or_series, True, False)
                    case 3:
                        upload(movie_or_series, False, False)
                # End

            case 4:
                # Start
                while True:
                    path = get_txt_path()

                    file = open(path, 'r', encoding='utf-8')
                    Lines = file.readlines()

                    match movie_or_series:
                        case 1:
                            # Start
                            for line in Lines:
                                image = input('Thumbnail URL:  ')
                                name = input('Movie name:  ')

                                hs = open(f"{name}.txt","a")

                                hs.write(f'[{name}]({make_embed(" ".join(line.split()), image)})\n')
                                hs.close()
                            # End

                        case 2:
                            # Start
                            image = input('Thumbnail URL:  ')
                            name = input('Series name:  ')

                            hs = open(f"{name}.txt","a")
                            i = 0
                            for line in Lines:
                                i += 1
                                hs.write(f'[{name} - Episode {i}]({make_embed(" ".join(line.split()), image)})\n')
                            # End

                    hs.close()

                    print(f"\nWould You Like To Do Another {movie_or_series_list[movie_or_series-1]}?")
                    if option(["Yes", "No"]) == 2:
                        break
                # End

            case 5:
                webhook_url, Fourm_Name, Thread_ID = get_webhook_url()
                file = open(get_txt_path(), 'r', encoding='utf-8')
                Lines = file.readlines()
                
                count = 0
                for line in Lines:
                    count += 1
                    sendmessage(line, webhook_url, Fourm_Name, Thread_ID)
                    time.sleep(0.2)
            case 6:
                return
    except _Menu:
        pass
        
    main()

main()
