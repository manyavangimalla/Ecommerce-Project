// Wait for the DOM to be fully loaded
document.addEventListener('DOMContentLoaded', function() {
    // Add event listeners for the payment method selection
    const creditCardRadio = document.getElementById('creditCard');
    const paypalRadio = document.getElementById('paypal');
    const creditCardForm = document.getElementById('creditCardForm');
    
    if (creditCardRadio && paypalRadio && creditCardForm) {
        creditCardRadio.addEventListener('change', function() {
            creditCardForm.style.display = 'block';
        });
        
        paypalRadio.addEventListener('change', function() {
            creditCardForm.style.display = 'none';
        });
    }
    
    // Product quantity validation
    const quantityInput = document.getElementById('quantity');
    if (quantityInput) {
        quantityInput.addEventListener('change', function() {
            if (parseInt(this.value) < 1) {
                this.value = 1;
            }
            // Get max from the max attribute
            const max = parseInt(this.getAttribute('max'));
            if (parseInt(this.value) > max) {
                this.value = max;
            }
        });
    }
    
    // Flash messages auto-dismiss
    const flashMessages = document.querySelectorAll('.alert:not(.alert-warning)');
    if (flashMessages.length > 0) {
        flashMessages.forEach(message => {
            setTimeout(function() {
                message.style.opacity = '0';
                message.style.transition = 'opacity 1s';
                setTimeout(function() {
                    message.remove();
                }, 1000);
            }, 5000);
        });
    }
});