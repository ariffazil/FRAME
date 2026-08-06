.PHONY: install test deploy clean health

VENV := /opt/frame/venv
APP := /opt/frame/app
SERVICE := frame-organ.service

install:
	@echo "=== FRAME Organ: Install ==="
	python3 -m venv $(VENV)
	$(VENV)/bin/pip install -e /root/FRAME/
	@echo "VENV ready at $(VENV)"

deploy:
	@echo "=== FRAME Organ: Deploy ==="
	mkdir -p $(APP) /var/lib/frame
	rsync -av --exclude='__pycache__' --exclude='*.pyc' --exclude='.git' \
		/root/FRAME/src/frame_organ/ $(APP)/frame_organ/
	cp /root/FRAME/pyproject.toml $(APP)/
	cp /root/FRAME/$(SERVICE) /etc/systemd/system/$(SERVICE)
	systemctl daemon-reload
	systemctl enable $(SERVICE)
	systemctl restart $(SERVICE)
	@echo "=== FRAME deployed. Probing health... ==="
	sleep 2 && curl -sf http://127.0.0.1:18085/health | python3 -m json.tool 2>/dev/null || echo "Health probe failed — check journalctl -u frame-organ"

health:
	curl -sf http://127.0.0.1:18085/health 2>/dev/null | python3 -m json.tool || echo "❌ FRAME DOWN"

probe:
	curl -sf http://127.0.0.1:18085/frame/probe 2>/dev/null | python3 -m json.tool || echo "❌ Probe failed"

clean:
	systemctl stop $(SERVICE) 2>/dev/null || true
	rm -rf $(APP)
	rm -f /etc/systemd/system/$(SERVICE)
