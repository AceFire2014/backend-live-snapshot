# backend-live-snapshot

A standalone service to create and offer preview_thumbnail(e.g. video, snapshot) for other websites(e.g. cams, aff)

## commands

- `$make run`: start application
- `$docker-compose down`: stop & clean application

## access video thumbnail

- `$curl localhost:8000/storage/videos/preview/mp4/{stream_name}.mp4`
