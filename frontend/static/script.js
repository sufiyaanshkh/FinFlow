// Function to fetch the latest transactions
function fetchTransactions() {
    fetch('/get_transactions')
        .then(response => response.json())
        .then(data => {
            let transactionList = document.getElementById('transaction-list');
            transactionList.innerHTML = '';
            data.forEach(transaction => {
                let li = document.createElement('li');
                li.textContent = `${transaction.description} - ₹${transaction.amount} (${transaction.category})`;
                transactionList.appendChild(li);
            });
        })
        .catch(error => console.log('Error fetching transactions:', error));
}

// Function to handle adding a transaction
document.getElementById('add-transaction-btn').addEventListener('click', function() {
    let description = document.getElementById('description').value;
    let amount = document.getElementById('amount').value;
    let category = document.getElementById('category').value;

    fetch('/add_transaction', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            description: description,
            amount: amount,
            category: category
        })
    })
    .then(response => response.json())
    .then(data => {
        // Once the transaction is added, update the transaction list
        if (data.success) {
            fetchTransactions();  // Fetch the updated transactions list
        }
    })
    .catch(error => console.log('Error adding transaction:', error));
});

// Initial fetch of transactions when the page loads
document.addEventListener('DOMContentLoaded', fetchTransactions);


function toggleSubcategories() {
  const category = document.getElementById('category').value;
  const subWrapper = document.getElementById('subcategory-wrapper');
  if (category === 'Expense') {
    subWrapper.style.display = 'block';
  } else {
    subWrapper.style.display = 'none';
  }
}
