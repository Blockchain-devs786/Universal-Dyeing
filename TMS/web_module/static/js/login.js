document.getElementById('loginForm').addEventListener('submit', async function(e) {
    e.preventDefault();
    e.stopPropagation();
    
    const formData = new FormData(this);
    const errorDiv = document.getElementById('error');
    const submitButton = this.querySelector('button[type="submit"]');
    
    errorDiv.textContent = '';
    submitButton.disabled = true;
    submitButton.textContent = 'Logging in...';
    
    try {
        const response = await fetch('/api/module/login', {
            method: 'POST',
            headers: {
                'Accept': 'application/json',
            },
            credentials: 'include',
            body: formData
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        
        if (data.success) {
            // Redirect to audit module after successful login
            window.location.href = data.redirect || '/audit';
        } else {
            errorDiv.textContent = data.message || 'Login failed';
            submitButton.disabled = false;
            submitButton.textContent = 'Login';
        }
    } catch (error) {
        errorDiv.textContent = 'Connection error. Please try again.';
        submitButton.disabled = false;
        submitButton.textContent = 'Login';
        console.error('Login error:', error);
    }
});
