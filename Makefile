VERSION := $(shell cat singletons/bot.py | grep "VERSION" | cut -d '"' -f2)

all: push-normal push-alpine

push-normal: normal
	docker push d.nyodev.xyz/ripple/fokabot:$(VERSION)

push-alpine: alpine
	docker push d.nyodev.xyz/ripple/fokabot:$(VERSION)

alpine:
	docker build -t d.nyodev.xyz/ripple/fokabot:$(VERSION)-alpine -f Dockerfile.alpine .

normal:
	docker build -t d.nyodev.xyz/ripple/fokabot:$(VERSION) .
