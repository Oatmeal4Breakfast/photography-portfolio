.PHONY: install test branch commit push pr ship export

install:
	uv sync

export:
	uv export --no-hashes --output-file requirements.txt

test:
	uv run pytest tests/ -v --tb=short

branch:
ifndef name
	$(error name is required. Usage: make branch name=feature/my-feature)
endif
	git checkout -b $(name)

commit: export
ifndef msg
	$(error msg is required. Usage: make commit msg="your message")
endif
	git add -A
	git commit -m "$(msg)"

push: test
	git push -u origin HEAD

pr:
ifndef title
	$(error title is required. Usage: make pr title="your title")
endif
	gh pr create --base main --title "$(title)" --body "$(body)"

ship: export test
ifndef msg
	$(error msg is required. Usage: make ship msg="commit msg" title="pr title")
endif
ifndef title
	$(error title is required. Usage: make ship msg="commit msg" title="pr title")
endif
	git add -A
	git commit -m "$(msg)"
	git push -u origin HEAD
	gh pr create --base main --title "$(title)" --body "$(body)"
