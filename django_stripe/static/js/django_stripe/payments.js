(async () => {
  'use strict';

  console.log(config)

  // Create references to the main form and its submit button.
  const form = document.getElementById('payment-form');
  const submitButton = document.querySelector('.payment-button');
  const confirmationElement = document.getElementById('confirmation');

  // Global variable to store the submit button text.
  let submitButtonPayText = 'Pay';

  const updateSubmitButtonPayText = (newText) => {
    submitButton.textContent = newText;
    submitButtonPayText = newText;
  };
  // Global variable to store the PaymentIntent object.
  let setupIntent;

  /**
   * Setup Stripe Elements.
   */

  // Create a Stripe client.
  const stripe = Stripe(config.stripePublishableKey);

  // Create an instance of Elements.
  const elements = stripe.elements();

  // Prepare the styles for Elements.
  const style = {
    base: {
      iconColor: '#666ee8',
      color: '#31325f',
      fontWeight: 400,
      fontFamily:
        '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Oxygen-Sans, Ubuntu, Cantarell, "Helvetica Neue", sans-serif',
      fontSmoothing: 'antialiased',
      fontSize: '15px',
      '::placeholder': {
        color: '#aab7c4',
      },
      ':-webkit-autofill': {
        color: '#666ee8',
      },
    },
  };

  /**
   * Implement a Stripe Card Element that matches the look-and-feel of the app.
   *
   * This makes it easy to collect debit and credit card payments information.
   */

  // Create a Card Element and pass some custom styles to it.
  const card = elements.create('card', {style, hidePostalCode: true});

  // Mount the Card Element on the page.
  card.mount('#card-element');

  // Monitor change events on the Card Element to display any errors.
  card.on('change', ({error}) => {
    const cardErrors = document.getElementById('card-errors');
    if (error) {
      cardErrors.textContent = error.message;
      cardErrors.classList.add('visible');
    } else {
      cardErrors.classList.remove('visible');
    }
    // Re-enable the Pay button.
    submitButton.disabled = false;
  });

  // Listen to changes to the user-selected country.
  form
    .querySelector('select[name=country]')
    .addEventListener('change', (event) => {
      event.preventDefault();
      selectCountry(event.target.value);
    });

  // Submit handler for our payment form.
  submitButton.addEventListener('click', async (event) => {
    event.preventDefault();
    console.log('Running submit');

    // Disable the Pay button to prevent multiple click events.
    submitButton.disabled = true;
    submitButton.textContent = 'Processing…';

    let paymentMethod = getSelectedPaymentMethod();
    console.log(paymentMethod);
    if (!paymentMethod){
        // Let Stripe.js handle the confirmation of the SetupIntent with the card Element.
        const valid = form.reportValidity();
        if (valid) {
          // Retrieve the user information from the form.
          const name = form.querySelector('input[name=name]').value;
          const email = config.user_email;
          const billingAddress = {
            country: form.querySelector('select[name=country] option:checked').value,
            line1: form.querySelector('input[name=address]').value,
            postal_code: form.querySelector('input[name=postal_code]').value,
            city: form.querySelector('input[name=city]').value,
            state: form.querySelector('input[name=state]').value,
          };

          setupIntent = setupIntent || await createSetupIntent();
          console.log("confirming card setup with setupIntent", setupIntent);
          const response = await stripe.confirmCardSetup(
              setupIntent.client_secret,
              {
                payment_method: {
                  card,
                  billing_details: {
                    name,
                    email,
                    address: billingAddress,
                  },
                },
              })
          const cardSetupSuccessful = handleCardSetupResponse(response);
          setupIntent = response.setupIntent;
          if (cardSetupSuccessful) {
            paymentMethod = setupIntent.payment_method;
            setupIntent = null;
          }
        }else{
            submitButton.disabled = false;
            submitButton.textContent = submitButtonPayText;
        }
    }

    if (paymentMethod) {
      console.log('Subscribing')
      const response = await createSubscription(paymentMethod);
      if (response.error) {
         confirmationElement.querySelector('.error-message').innerText = error.message;
         mainElement.classList.add('error');

      }else{
          mainElement.classList.add('success');
      }
      console.log(response);
    }
  });

  // Handle payment setup result
  const handleCardSetupResponse = (handleCardSetupResponse) => {
    const {setupIntent, error} = handleCardSetupResponse;

    const mainElement = document.getElementById('main');

    if (error && error.type === 'validation_error') {
      mainElement.classList.remove('processing');
      mainElement.classList.remove('receiver');
      submitButton.disabled = false;
      submitButton.textContent = submitButtonPayText;
      return false;
    } else if (error) {
      mainElement.classList.remove('processing');
      mainElement.classList.remove('receiver');
      confirmationElement.querySelector('.error-message').innerText =
        error.message;
      mainElement.classList.add('error');
      return false;
    } else if (setupIntent.status === 'succeeded') {
      // Success! Payment is confirmed. Update the interface to display the confirmation screen.
      mainElement.classList.remove('processing');
      mainElement.classList.remove('receiver');
      // Update the note about successful subscription.
      confirmationElement.querySelector('.note').innerText =
        'Your payment details have been confirmed.';
      return true;
    } else if (setupIntent.status === 'processing') {
      // Success! Now waiting for payment method confirmation.
      mainElement.classList.remove('processing');
      confirmationElement.querySelector('.note').innerText =
        'Your subscription will become active soon as your payment method is confirmed.';
      return true;
    } else if (setupIntent.status === 'requires_payment_method') {
      // Failure. Requires new PaymentMethod, show last payment error message.
      mainElement.classList.remove('processing');
      confirmationElement.querySelector('.error-message').innerText = setupIntent.last_setup_error || 'Payment failed';
      mainElement.classList.add('error');
      return false;
    } else {
      // Payment method setup has failed.
      mainElement.classList.remove('success');
      mainElement.classList.remove('processing');
      mainElement.classList.remove('receiver');
      mainElement.classList.add('error');
      return false;
    }
  };

  const mainElement = document.getElementById('main');

  mainElement.classList.add('checkout');

    // Create the PaymentIntent with the cart details.
  document.getElementById('main').classList.remove('loading');

  /**
   * Display the relevant payment methods for a selected country.
   */

  // List of relevant countries for the payment methods supported in this demo.
  // Read the Stripe guide: https://stripe.com/payments/payment-methods-guide
  const paymentMethods = {
    card: {
      name: 'Card',
      flow: 'none',
    },
  };

  // Update the main button to reflect the payment method being selected.
  const updateButtonLabel = (paymentMethod, bankName) => {
    let name = paymentMethods[paymentMethod].name;
    let label = `Subscribe`;
    updateSubmitButtonPayText(label);
  };

  const selectCountry = (country) => {
    const selector = document.getElementById('country');
    selector.querySelector(`option[value=${country}]`).selected = 'selected';
    selector.className = `field ${country.toLowerCase()}`;

    // Trigger the methods to show relevant fields and payment methods on page load.
    showRelevantFormFields();
  };

  // Show only form fields that are relevant to the selected country.
  const showRelevantFormFields = (country) => {
    if (!country) {
      country = form.querySelector('select[name=country] option:checked').value;
    }
    const zipLabel = form.querySelector('label.zip');
    // Only show the state input for the United States.
    zipLabel.parentElement.classList.toggle(
      'with-state',
      ['AU', 'US'].includes(country)
    );
    // Update the ZIP label to make it more relevant for each country.
    const zipInput = form.querySelector('label.zip input');
    const zipSpan = form.querySelector('label.zip span');
    switch (country) {
      case 'US':
        zipSpan.innerText = 'ZIP';
        zipInput.placeholder = '94103';
        break;
      case 'GB':
        zipSpan.innerText = 'Postcode';
        zipInput.placeholder = 'EC1V 9NR';
        break;
      case 'AU':
        zipSpan.innerText = 'Postcode';
        zipInput.placeholder = '3000';
        break;
      default:
        zipSpan.innerText = 'Postal Code';
        zipInput.placeholder = '94103';
        break;
    }

    // Update the 'City' to appropriate name
    const cityInput = form.querySelector('label.city input');
    const citySpan = form.querySelector('label.city span');
    switch (country) {
      case 'AU':
        citySpan.innerText = 'City / Suburb';
        cityInput.placeholder = 'Melbourne';
        break;
      default:
        citySpan.innerText = 'City';
        cityInput.placeholder = 'San Francisco';
        break;
    }
  };

  // Show only the payment methods that are relevant to the selected country.
  const showRelevantPaymentMethods = (country) => {
    if (!country) {
      country = form.querySelector('select[name=country] option:checked').value;
    }
    const paymentInputs = form.querySelectorAll('input[name=payment]');
    for (let i = 0; i < paymentInputs.length; i++) {
      let input = paymentInputs[i];
      input.parentElement.classList.toggle(
        'visible',
        input.value === 'card' ||
          (config.paymentMethods.includes(input.value) &&
            paymentMethods[input.value].countries.includes(country) &&
            paymentMethods[input.value].currencies.includes(config.currency))
      );
    }

    // Hide the tabs if card is the only available option.
    const paymentMethodsTabs = document.getElementById('payment-methods');
    paymentMethodsTabs.classList.toggle(
      'visible',
      paymentMethodsTabs.querySelectorAll('li.visible').length > 1
    );

    // Check the first payment option again.
    paymentInputs[0].checked = 'checked';
    form.querySelector('.payment-info.card').classList.add('visible');
    updateButtonLabel(paymentInputs[0].value);
  };

  // Listen to changes to the payment method selector.
  for (let input of document.querySelectorAll('input[name=payment]')) {
    input.addEventListener('change', (event) => {
      event.preventDefault();
      const payment = form.querySelector('input[name=payment]:checked').value;
      const flow = paymentMethods[payment].flow;

      // Update button label.
      updateButtonLabel(event.target.value);

      // Show the relevant details, whether it's an extra element or extra information for the user.
      form
        .querySelector('.payment-info.card')
        .classList.toggle('visible', payment === 'card');
    });
  }

  // Select the default country from the config on page load.
  let country = config.country;
  selectCountry(country);
})();