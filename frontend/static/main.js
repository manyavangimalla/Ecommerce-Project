// Wait for the DOM to be fully loaded
document.addEventListener('DOMContentLoaded', function () {
    // Add event listeners for the payment method selection
    const creditCardRadio = document.getElementById('creditCard');
    const paypalRadio = document.getElementById('paypal');
    const creditCardForm = document.getElementById('creditCardForm');

    if (creditCardRadio && paypalRadio && creditCardForm) {
        creditCardRadio.addEventListener('change', function () {
            creditCardForm.style.display = 'block';
        });

        paypalRadio.addEventListener('change', function () {
            creditCardForm.style.display = 'none';
        });
    }

    // Product quantity validation
    const quantityInput = document.getElementById('quantity');
    if (quantityInput) {
        quantityInput.addEventListener('change', function () {
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
            setTimeout(function () {
                message.style.opacity = '0';
                message.style.transition = 'opacity 1s';
                setTimeout(function () {
                    message.remove();
                }, 1000);
            }, 5000);
        });
    }

    // Call fetchProducts when the DOM is loaded
    fetchProducts();
});

// Fetch products dynamically and display them
async function fetchProducts() {
    const productsContainer = document.getElementById('productsContainer');
    if (!productsContainer) return;

    try {
        const response = await fetch(`${API_URL}/api/products`);
        if (!response.ok) {
            throw new Error('Failed to fetch products');
        }

        const products = await response.json();
        productsContainer.innerHTML = '';
        products.forEach(product => {
            const productCard = document.createElement('div');
            productCard.className = 'col-md-4';
            productCard.innerHTML = `
                <div class="card mb-4 shadow-sm">
                    <img src="${product.image || 'placeholder.jpg'}" class="card-img-top" alt="${product.name}">
                    <div class="card-body">
                        <h5 class="card-title">${product.name}</h5>
                        <p class="card-text">${product.description}</p>
                        <div class="d-flex justify-content-between align-items-center">
                            <span class="text-muted">$${product.price.toFixed(2)}</span>
                            <a href="/product/${product.id}" class="btn btn-sm btn-primary">View</a>
                        </div>
                    </div>
                </div>
            `;
            productsContainer.appendChild(productCard);
        });
    } catch (error) {
        console.error('Error fetching products:', error);
        productsContainer.innerHTML = '<p class="text-danger">Failed to load products. Please try again later.</p>';
    }
}