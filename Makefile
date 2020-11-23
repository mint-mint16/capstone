prepare:
	@pip3 install pipreqs

sync_dep:
	@pipreqs . --force

dep:
	@pip3 install -r requirements.txt

run:
	@python3 manage.py runserver