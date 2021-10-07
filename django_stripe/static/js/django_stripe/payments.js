(async () => {
  'use strict';

  // Get required config
  const email = config.email;
  let country = config.country;

  // Create references to the main form and its submit button.
  const form = document.getElementById('payment-form');
  const submitButton = document.querySelector('.payment-button');
  const confirmationElement = document.getElementById('confirmation');

  // Global variable to store the submit button text.
  let submitButtonPayText = submitButton.textContent;

  const updateSubmitButtonPayText = (newText) => {
    submitButton.textContent = newText;
  };

  // Global variable to store the SetupIntent object.
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
      submitButton.disabled = true;
    } else if (!config.subscriptionInfo.sub_id && !selectedPriceId){
      cardErrors.textContent = "Please select the price option you wish to subscribe with";
      cardErrors.classList.add('visible');
      submitButton.disabled = true;
    }
    else {
      cardErrors.classList.remove('visible');
          // Re-enable the Subscribe button.
      submitButton.disabled = false;
    }
  });

  function scrollToTop(){
    window.scrollTo(0, 0);
  }

  function capitalizeFirstLetter(string) {
    return string.charAt(0).toUpperCase() + string.slice(1);
  }

  function scrollToElem(selector){
    const rect = document.querySelector(selector).getBoundingClientRect();
    scrollTo({top: rect.y, left: rect.x, behavior: 'smooth'})
  }

  function onError(message){
      if (message) {
        confirmationElement.querySelector('.error-message').innerText = capitalizeFirstLetter(message);
      }
      mainElement.classList.remove('processing');
      mainElement.classList.add('error');
      scrollToTop();
  }

  function onSuccess(message){
      if (message) {
        confirmationElement.querySelector('.note').innerText = capitalizeFirstLetter(message);
      }
      mainElement.classList.remove('processing');
      mainElement.classList.add('success');
      mainElement.classList.remove('checkout');
      scrollToTop();
  }

  // Listen to changes to the user-selected country.
  form
    .querySelector('select[name=country]')
    .addEventListener('change', (event) => {
      event.preventDefault();
      selectCountry(event.target.value);
    });

  // Submit handler for our subscription form.
  submitButton.addEventListener('click', async (event) => {
    event.preventDefault();

    // Disable the Pay button to prevent multiple click events.
    submitButton.disabled = true;
    submitButton.textContent = 'Processing…';
    mainElement.classList.add('processing');
    mainElement.classList.remove('error');
    mainElement.classList.remove('success')

    // Let Stripe.js handle the confirmation of the SetupIntent with the card Element.
    const valid = form.reportValidity();
    if (valid) {
      // Retrieve the user information from the form.
      const name = form.querySelector('input[name=name]').value;
      const billingAddress = {
        country: form.querySelector('select[name=country] option:checked').value,
        line1: form.querySelector('input[name=address]').value,
        postal_code: form.querySelector('input[name=postal_code]').value,
        city: form.querySelector('input[name=city]').value,
        state: form.querySelector('input[name=state]').value,
      };

      setupIntent = setupIntent || await createSetupIntent();

      if (setupIntent.error) {
        onError(setupIntent.error);
        setupIntent = null;
      }else{
        const confirmCardSetupResponse = await stripe.confirmCardSetup(
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
        const cardSetupSuccessful = handleCardSetupResponse(confirmCardSetupResponse);
        setupIntent = confirmCardSetupResponse.setupIntent;
        if (cardSetupSuccessful) {
          const paymentMethod = setupIntent.payment_method;
          setupIntent = null;
          let subscriptionResponse;
          if (config.subscriptionInfo.sub_id) {
            subscriptionResponse = await modifySubscription(config.subscriptionInfo.sub_id, paymentMethod);
          } else {
            subscriptionResponse = await createSubscription(paymentMethod);
          }
          if (subscriptionResponse.error) {
            onError(subscriptionResponse.error)
          } else if (subscriptionResponse.status !== "active"){
            onSuccess("Your subscription is not yet active as your payment method has not been processed.");
          }else{
            onSuccess();
          }
        } else {
          submitButton.disabled = false;
          submitButton.textContent = submitButtonPayText;
        }
      }
    }else{
        submitButton.disabled = false;
        submitButton.textContent = submitButtonPayText;
    }
  });


  // Handle payment setup result
  const handleCardSetupResponse = (handleCardSetupResponse) => {
    const {setupIntent, error} = handleCardSetupResponse;

    const mainElement = document.getElementById('main');

    if (error && error.type === 'validation_error') {
      submitButton.disabled = false;
      submitButton.textContent = submitButtonPayText;
      return false;
    } else if (error) {
      onError(error.message);
      return false;
    } else if (setupIntent.status === 'succeeded') {
      // Success! Payment is confirmed. Update the interface to display the confirmation screen.
      // Update the note about successful subscription.
      //confirmationElement.querySelector('.note').innerText = 'Your payment details have been confirmed.';
      return true;
    } else if (setupIntent.status === 'processing') {
      // Success! Now waiting for payment method confirmation.
      confirmationElement.querySelector('.note').innerText =
        'Your subscription will become active soon as your payment method is confirmed.';
      return true;
    } else if (setupIntent.status === 'requires_payment_method') {
      // Failure. Requires new PaymentMethod, show last payment error message.
      onError(setupIntent.last_setup_error.message || 'Payment failed');
      return false;
    } else {
      // Payment method setup has failed.
      onError();
      return false;
    }
  };

  const mainElement = document.getElementById('main');

  mainElement.classList.add('checkout');

  document.getElementById('main').classList.remove('loading');

  const paymentMethods = {
    card: {
      name: 'Card',
      flow: 'none',
    },
  };

  // Update the main button to reflect the payment method being selected.
  const updateButtonLabel = () => {
    updateSubmitButtonPayText(submitButtonPayText);
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

  // Select the default country from the config on page load.

  selectCountry(country);

  const cancelSubscriptionButton = document.querySelector('.cancel-subscription-button');
  if (cancelSubscriptionButton) {
    cancelSubscriptionButton.addEventListener('click', async function () {
      const result = await cancelSubscription(config.subscriptionInfo.sub_id);
      if (result.error) {
        confirmationElement.querySelector('#error-header').innerText = "We were unable to cancel your subscription";
        confirmationElement.querySelector('#error-text').innerText = "";

        onError(result.error);

      } else {
        console.log(result);
        if (result.cancel_at) {
          confirmationElement.querySelector('#success-header').innerText = `Your subscription will be cancelled on ${result.cancel_at}`;
        }else{
          confirmationElement.querySelector('#success-header').innerText = `Your subscription has been cancelled`;
        }
        confirmationElement.querySelector('#success-text').innerText = "Sorry to see you go";
        onSuccess();
      }
    });
  }

  function toggleSummary() {
    const summary = document.getElementById('summary');
    summary.classList.toggle(
      'visible',
      selectedPriceId
    );
  }

  function onPriceClick(event){
    const priceElem = event.target;
    selectedPriceId = priceElem.id;
    document.querySelector('.total-price').textContent = getPriceText(priceElem);
    toggleSummary();
    const firstFieldElem = document.querySelector('input');
    scrollToElem('input[name=name]');
    firstFieldElem.focus();
  }

   document.querySelectorAll(".price-selection")
       .forEach(elem => {
          elem.addEventListener('click', onPriceClick)
    });

})();

document.addEventListener('DOMContentLoaded', function() {
  var elems = document.querySelectorAll('.modal');
  var instances = M.Modal.init(elems);
});