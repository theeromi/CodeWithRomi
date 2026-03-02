# BOOKSTACK 
## "Self-Hosted Notion Alternative: BookStack for YouTube Creators"

**Video Length:** 12-15 minutes  
**Difficulty:** Beginner-friendly  
**Channel:** @CodeWithRomii

---

## 🎯 VIDEO GOALS

1. Install BookStack with Docker Compose
2. Configure with APP_KEY
3. Organize YouTube scripts and ideas
4. Show practical use cases for content creators
5. Demo importing markdown files
6. 100% success - clean, simple tutorial

---


### INSTALLATION PART 1: SETUP 


```bash
mkdir ~/bookstack
cd ~/bookstack
```

**[In directory]**

"Now BookStack needs a database, so we're going to use Docker Compose to set up both BookStack AND MariaDB together. Don't worry, I'll show you exactly what to do."


"Create the docker-compose file:"

```bash
nano docker-compose.yml
```





```yaml
version: "3"
services:
  bookstack:
    image: lscr.io/linuxserver/bookstack
    container_name: bookstack
    environment:
      - PUID=1000
      - PGID=1000
      - APP_URL=http://192.168.1.248:6875
      - DB_HOST=bookstack_db
      - DB_PORT=3306
      - DB_DATABASE=bookstackapp
      - DB_USERNAME=bookstack
      - DB_PASSWORD=bookstack
    volumes:
      - ./config:/config
    ports:
      - 6875:80
    restart: unless-stopped
    depends_on:
      - bookstack_db

  bookstack_db:
    image: lscr.io/linuxserver/mariadb
    container_name: bookstack_db
    environment:
      - PUID=1000
      - PGID=1000
      - MYSQL_ROOT_PASSWORD=bookstack
      - MYSQL_DATABASE=bookstackapp
      - MYSQL_USER=bookstack
      - MYSQL_PASSWORD=bookstack
    volumes:
      - ./db:/config
    restart: unless-stopped
```



"Save with Ctrl+X, then Y, then Enter."

---

### INSTALLATION PART 2: APP KEY (4:30 - 6:00)

**[Back in terminal]**

"Now here's the important part - BookStack needs an encryption key. Let's generate one:"

```bash
docker run -it --rm --entrypoint /bin/bash lscr.io/linuxserver/bookstack:latest appkey
```

**[Command runs, shows output]**

"Copy this entire key - it'll look like `base64:` followed by random characters."

**[Highlight and copy the key]**

```
base64:
```

**[Open nano again]**

"Now edit the docker-compose file again:"

```bash
nano docker-compose.yml
```

**[Navigate to bookstack environment section]**

"Add this line under APP_URL:"

```yaml
      - APP_KEY=base64:
```



```yaml
    environment:
      - PUID=1000
      - PGID=1000
      - APP_URL=http://192.168.1.248:6875
      - APP_KEY=base64:
      - DB_HOST=bookstack_db
```

**[Save again]**

"Save it. Now we're ready to start BookStack!"

---

### INSTALLATION PART 3: LAUNCH 

**[Terminal]**

"Start the containers:"

```bash
docker compose up -d
```


```bash
docker compose ps
```



