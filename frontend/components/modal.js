// Modal component
class Modal {
    constructor() {
        this.container = document.getElementById('modal-container');
    }

    confirm(title, message, onConfirm, onCancel = null) {
        const modalHtml = `
            <div class="modal-overlay" id="confirm-modal">
                <div class="modal">
                    <h2>${title}</h2>
                    <p>${message}</p>
                    <div class="modal-buttons">
                        <button class="btn btn-secondary" id="modal-cancel">Cancel</button>
                        <button class="btn btn-primary" id="modal-confirm">Confirm</button>
                    </div>
                </div>
            </div>
        `;

        this.container.innerHTML = modalHtml;

        const modal = document.getElementById('confirm-modal');
        const confirmBtn = document.getElementById('modal-confirm');
        const cancelBtn = document.getElementById('modal-cancel');

        confirmBtn.addEventListener('click', () => {
            this.close();
            if (onConfirm) onConfirm();
        });

        cancelBtn.addEventListener('click', () => {
            this.close();
            if (onCancel) onCancel();
        });

        // Close on overlay click
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                this.close();
                if (onCancel) onCancel();
            }
        });
    }

    show(title, content) {
        const modalHtml = `
            <div class="modal-overlay" id="info-modal">
                <div class="modal">
                    <h2>${title}</h2>
                    <div>${content}</div>
                    <div class="modal-buttons">
                        <button class="btn btn-primary" id="modal-ok">OK</button>
                    </div>
                </div>
            </div>
        `;

        this.container.innerHTML = modalHtml;

        const modal = document.getElementById('info-modal');
        const okBtn = document.getElementById('modal-ok');

        okBtn.addEventListener('click', () => {
            this.close();
        });

        // Close on overlay click
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                this.close();
            }
        });
    }

    resetOptions(onConfirm) {
        const modalHtml = `
            <div class="modal-overlay" id="reset-modal">
                <div class="modal">
                    <h2>Reset Grid</h2>
                    <p>Choose reset options:</p>
                    <div style="margin: 20px 0;">
                        <label style="display: block; margin-bottom: 10px;">
                            <input type="radio" name="reset-option" value="cancel-only" checked>
                            Cancel orders only
                        </label>
                        <label style="display: block;">
                            <input type="radio" name="reset-option" value="cancel-close">
                            Cancel orders and close positions
                        </label>
                    </div>
                    <div class="modal-buttons">
                        <button class="btn btn-secondary" id="modal-cancel">Cancel</button>
                        <button class="btn btn-warning" id="modal-reset">Reset</button>
                    </div>
                </div>
            </div>
        `;

        this.container.innerHTML = modalHtml;

        const modal = document.getElementById('reset-modal');
        const resetBtn = document.getElementById('modal-reset');
        const cancelBtn = document.getElementById('modal-cancel');

        resetBtn.addEventListener('click', () => {
            const option = document.querySelector('input[name="reset-option"]:checked').value;
            this.close();
            if (onConfirm) onConfirm(option === 'cancel-close');
        });

        cancelBtn.addEventListener('click', () => {
            this.close();
        });

        // Close on overlay click
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                this.close();
            }
        });
    }

    close() {
        this.container.innerHTML = '';
    }
}

// Global modal instance
const modal = new Modal();