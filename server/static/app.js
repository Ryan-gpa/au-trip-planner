const app = {
  apiKey: localStorage.getItem('tripPlannerApiKey') || '',
  currentProfile: null,
  allProfiles: [],
  selectedFlight: null,
  selectedHotel: null,

  init() {
    this.fetchProfiles();
  },

  fetchProfiles() {
    fetch('/staff')
      .then(res => res.json())
      .then(data => {
        this.allProfiles = data;
        this.populateUserSelect();
      })
      .catch(e => console.error(e));
  },

  navigate(view) {
    document.getElementById('nav-trip').classList.remove('active');
    document.getElementById('nav-profile').classList.remove('active');
    document.getElementById('nav-history').classList.remove('active');
    
    document.getElementById('view-trip').classList.add('hidden');
    document.getElementById('view-profile').classList.add('hidden');
    document.getElementById('view-history').classList.add('hidden');
    
    document.getElementById(`nav-${view}`).classList.add('active');
    document.getElementById(`view-${view}`).classList.remove('hidden');
    
    if (view === 'history') {
      this.loadHistory();
    }
  },

  // ---- CRM / ADDRESS BOOK LOGIC ----
  mockContacts: [
    { name: "John Doe", company: "Acme Corp", address: "100 Collins St, Melbourne" },
    { name: "Jane Smith", company: "Globex Inc", address: "1 William St, Brisbane" },
    { name: "Robert California", company: "Sabre", address: "1 Martin Place, Sydney" }
  ],

  openAddressBook() {
    const modal = document.getElementById('address-book-modal');
    const list = document.getElementById('address-book-list');
    
    list.innerHTML = this.mockContacts.map((c, i) => `
      <div class="contact-card" onclick="app.selectContact(${i})">
        <div class="contact-name">${c.name}</div>
        <div class="contact-company">${c.company}</div>
        <div class="contact-address">${c.address}</div>
      </div>
    `).join('');
    
    modal.classList.remove('hidden');
  },

  closeAddressBook() {
    document.getElementById('address-book-modal').classList.add('hidden');
  },

  selectContact(index) {
    const contact = this.mockContacts[index];
    document.getElementById('client-name').value = contact.company;
    document.getElementById('client-address').value = contact.address;
    
    // Auto trigger the map search if address exists
    if (contact.address) {
      this.searchAddress(contact.address);
    }
    
    this.closeAddressBook();
  },

  importFromMeeting() {
    // Mock extracting from an Outlook Meeting Invite
    document.getElementById('client-name').value = "Wayne Enterprises (From Outlook)";
    document.getElementById('client-address').value = "111 Eagle St, Brisbane";
    this.searchAddress("111 Eagle St, Brisbane");
    this.closeAddressBook();
  },

  // ---- PROFILE MANAGEMENT ----

  populateUserSelect() {
    const select = document.getElementById('profile-user-select');
    const tripSelect = document.getElementById('trip-executive-select');
    
    const optionsHtml = '<option value="">Guest</option>' + 
      this.allProfiles.map(p => `<option value="${p.name}">${p.name}</option>`).join('');
      
    if (select) select.innerHTML = '<option value="">Select a user...</option>' + this.allProfiles.map(p => `<option value="${p.name}">${p.name}</option>`).join('');
    if (tripSelect) tripSelect.innerHTML = optionsHtml;
  },

  loadSelectedProfile() {
    const name = document.getElementById('profile-user-select').value;
    if (!name) {
      document.getElementById('profile-details-section').classList.add('hidden');
      return;
    }

    const p = this.allProfiles.find(x => x.name === name);
    this.currentProfile = p;

    document.getElementById('profile-details-section').classList.remove('hidden');
    document.getElementById('profile-name').value = p.name || '';
    document.getElementById('profile-role').value = p.role || '';
    document.getElementById('profile-tier').value = p.tier || 'standard';
    document.getElementById('profile-home').value = p.home_city || '';
    document.getElementById('profile-email').value = p.email || '';
    document.getElementById('profile-phone').value = p.phone || '';
    document.getElementById('profile-notes').value = p.notes || '';

    this.renderLoyaltyList('ff', p.frequent_flyer || []);
    this.renderLoyaltyList('hotel', p.hotel_loyalty || []);
    document.getElementById('profile-msg').textContent = '';
  },

  renderLoyaltyList(type, items) {
    const list = document.getElementById(`profile-${type}-list`);
    list.innerHTML = '';
    items.forEach(item => {
      this.addLoyaltyRow(type, item.program, item.number);
    });
  },

  addLoyaltyRow(type, program = '', number = '') {
    const list = document.getElementById(`profile-${type}-list`);
    const div = document.createElement('div');
    div.className = 'loyalty-item';
    div.innerHTML = `
      <input type="text" placeholder="Program (e.g. Qantas)" class="loyalty-program" value="${program}">
      <input type="text" placeholder="Number" class="loyalty-number" value="${number}">
      <button class="secondary" onclick="this.parentElement.remove()">X</button>
    `;
    list.appendChild(div);
  },

  getLoyaltyData(type) {
    const items = [];
    const rows = document.getElementById(`profile-${type}-list`).querySelectorAll('.loyalty-item');
    rows.forEach(r => {
      const program = r.querySelector('.loyalty-program').value.trim();
      const number = r.querySelector('.loyalty-number').value.trim();
      if (program && number) {
        items.push({ program, number });
      }
    });
    return items;
  },

  async saveProfile() {
    const name = this.currentProfile.name;
    const msg = document.getElementById('profile-msg');
    msg.style.color = 'var(--text-muted)';
    msg.textContent = 'Saving...';

    const payload = {
      name: name,
      role: document.getElementById('profile-role').value,
      tier: document.getElementById('profile-tier').value,
      home_city: document.getElementById('profile-home').value,
      email: document.getElementById('profile-email').value,
      phone: document.getElementById('profile-phone').value,
      frequent_flyer: this.getLoyaltyData('ff'),
      hotel_loyalty: this.getLoyaltyData('hotel'),
      notes: document.getElementById('profile-notes').value
    };

    try {
      const res = await fetch(`/staff/${encodeURIComponent(name)}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json', 'x-api-key': this.apiKey },
        body: JSON.stringify(payload)
      });
      if (!res.ok) throw new Error("Failed to update profile");
      const updated = await res.json();
      
      // Update in local cache
      const idx = this.allProfiles.findIndex(x => x.name === name);
      if (idx !== -1) this.allProfiles[idx] = updated;
      
      msg.style.color = 'var(--accent)';
      msg.textContent = 'Profile saved successfully.';
    } catch (e) {
      msg.style.color = '#ef4444';
      msg.textContent = e.message;
    }
  },

  // ---- TRIP PLANNER ----

  async searchAddress(query) {
    const dropdown = document.getElementById('address-suggestions');
    if (!query || query.length < 3) {
      dropdown.classList.add('hidden');
      return;
    }
    try {
      const res = await fetch(`https://photon.komoot.io/api/?q=${encodeURIComponent(query + ' australia')}&limit=5`);
      const data = await res.json();
      if (data.features && data.features.length > 0) {
        dropdown.innerHTML = data.features.map(f => {
          const p = f.properties;
          const label = `${p.housenumber || ''} ${p.street || p.name || ''}, ${p.district || p.locality || p.city || ''} ${p.state || ''} ${p.postcode || ''}`.trim().replace(/^,\s*/, '').replace(/\s+/g, ' ');
          return `<div class="suggestion-item" onclick="app.selectAddress('${label.replace(/'/g, "\\'")}')">${label}</div>`;
        }).join('');
        dropdown.classList.remove('hidden');
      } else {
        dropdown.classList.add('hidden');
      }
    } catch (e) {
      dropdown.classList.add('hidden');
    }
  },

  selectAddress(address) {
    document.getElementById('client-address').value = address;
    document.getElementById('address-suggestions').classList.add('hidden');
  },

  async checkCalendar(date, dest, cname, caddress) {
    const alertBox = document.getElementById('calendar-section');
    const content = document.getElementById('calendar-alert-content');
    alertBox.classList.remove('hidden');
    content.innerHTML = '<strong>Calendar Assistant:</strong> Checking your schedule...';
    content.className = 'calendar-alert';

    try {
      let url = `/calendar/check?date=${date}&dest=${dest}`;
      if (cname) url += `&client_name=${encodeURIComponent(cname)}`;
      if (caddress) url += `&client_address=${encodeURIComponent(caddress)}`;
      
      const res = await fetch(url, { headers: { 'x-api-key': this.apiKey } });
      const data = await res.json();
      if (data.events && data.events.length > 0) {
        content.className = 'calendar-alert warning';
        content.innerHTML = `
          <div class="calendar-alert-header">
            <svg width="16" height="16" fill="currentColor" viewBox="0 0 24 24"><path d="M19 4h-1V3a1 1 0 00-2 0v1H8V3a1 1 0 00-2 0v1H5a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2V6a2 2 0 00-2-2zm0 16H5V10h14v10zm0-12H5V6h14v2z"/></svg>
            Mocked Microsoft Outlook / Gmail Calendar Integration
          </div>
          <div><strong>📅 Meeting Conflict Detected:</strong> ${data.recommendation}</div>
        `;
        
        // Populate Trip Context
        const ctxBox = document.getElementById('trip-context');
        ctxBox.classList.remove('hidden');
        document.getElementById('context-profile-name').textContent = this.currentProfile ? this.currentProfile.name : "Guest";
        
        const scheduleHtml = data.events.map(e => `
          <div><strong>${e.start.split('T')[1].substring(0,5)} - ${e.end.split('T')[1].substring(0,5)}:</strong> ${e.subject} <br/> <small>📍 ${e.location}</small></div>
        `).join('');
        document.getElementById('context-schedule').innerHTML = scheduleHtml;
        
        // Mock Logistics Calculation
        this.clientAddress = data.client_address || dest;
        document.getElementById('context-distances').innerHTML = `
          Estimated travel time from Airport to ${this.clientAddress} is ~45 mins. <br/>
          <em>Hotel distances will be estimated upon selection.</em>
        `;
        
        // Initialize Map
        const mapFrame = document.getElementById('context-map');
        if (mapFrame) {
          mapFrame.src = `https://maps.google.com/maps?q=${encodeURIComponent(this.clientAddress)}&output=embed`;
        }
        
      } else {
        content.innerHTML = `<strong>Calendar:</strong> No conflicts found for ${date}.`;
      }
    } catch (e) {
      alertBox.classList.add('hidden');
    }
  },

  async searchTrip() {
    const origin = document.getElementById('origin').value;
    const dest = document.getElementById('destination').value;
    const depart = document.getElementById('depart').value;
    const clientName = document.getElementById('client-name').value;
    const clientAddress = document.getElementById('client-address').value;
    const execName = document.getElementById('trip-executive-select').value;
    
    if (execName) {
      this.currentProfile = this.allProfiles.find(x => x.name === execName);
    } else {
      this.currentProfile = null;
    }
    
    if (!origin || !dest || !depart) {
      alert("Please fill in Origin, Destination, and Depart Date.");
      return;
    }

    document.getElementById('search-loading').classList.remove('hidden');
    document.getElementById('flight-results-container').classList.add('hidden');
    document.getElementById('hotel-results-container').classList.add('hidden');

    this.checkCalendar(depart, dest, clientName, clientAddress);

    this.selectedOutboundFlight = null;
    this.selectedReturnFlight = null;
    this.selectedHotel = null;
    this.updateSummary();

    const passengers = document.getElementById('passengers').value;
    const flightSource = document.getElementById('flightSource').value;
    const ret = document.getElementById('returnDate').value;

    const fParams = new URLSearchParams({
      origin: origin, destination: dest, depart: depart, passengers: passengers, source: flightSource
    });
    if (ret) fParams.append('return_date', ret);

    const hParams = new URLSearchParams({
      city: dest, country: 'AU', checkin: depart, checkout: ret || this.addDays(depart, 1), adults: passengers
    });

    try {
      const [fRes, hRes] = await Promise.all([
        fetch('/flights/search?' + fParams.toString(), { headers: { 'x-api-key': this.apiKey } }),
        fetch('/hotels/search?' + hParams.toString(), { headers: { 'x-api-key': this.apiKey } })
      ]);

      const fData = await fRes.json();
      const hData = await hRes.json();

      document.getElementById('search-loading').classList.add('hidden');
      
      // Render Flights
      const fCont = document.getElementById('flightResults');
      const fRetCont = document.getElementById('returnFlightResults');
      const fRetSec = document.getElementById('return-flight-section');
      
      document.getElementById('flight-results-container').classList.remove('hidden');
      
      // Render Outbound
      if (fRes.ok && fData.outbound_offers && fData.outbound_offers.length > 0) {
        fCont.innerHTML = fData.outbound_offers.map((f, i) => {
          let outText = "Time Unavailable";
          if (f.departing_at && f.arriving_at) {
            outText = `Depart: ${f.departing_at.split('T')[1].slice(0, 5)} - Arrive: ${f.arriving_at.split('T')[1].slice(0, 5)}`;
          }
          return `
            <div class="option-card" id="flight-out-opt-${i}" onclick="app.selectFlight('out', ${i}, ${parseFloat(f.total_amount || 0)}, '${f.airline || f.provider}', '${f.total_currency || f.currency}', '${f.offer_id}')">
              <div class="card-header">
                <h3 class="card-title">${f.airline || f.provider}</h3>
                <span class="card-price">$${f.total_amount}</span>
              </div>
              <div class="card-detail">${outText}</div>
              <span class="source-tag">${fData.source}</span>
            </div>
          `;
        }).join('');
      } else {
        fCont.innerHTML = `<p>${fData.detail || 'No outbound flights found.'}</p>`;
      }

      // Render Return
      if (ret) {
        fRetSec.classList.remove('hidden');
        if (fRes.ok && fData.return_offers && fData.return_offers.length > 0) {
          fRetCont.innerHTML = fData.return_offers.map((f, i) => {
            let retText = "Time Unavailable";
            if (f.departing_at && f.arriving_at) {
              retText = `Depart: ${f.departing_at.split('T')[1].slice(0, 5)} - Arrive: ${f.arriving_at.split('T')[1].slice(0, 5)}`;
            }
            return `
              <div class="option-card" id="flight-ret-opt-${i}" onclick="app.selectFlight('ret', ${i}, ${parseFloat(f.total_amount || 0)}, '${f.airline || f.provider}', '${f.total_currency || f.currency}', '${f.offer_id}')">
                <div class="card-header">
                  <h3 class="card-title">${f.airline || f.provider}</h3>
                  <span class="card-price">$${f.total_amount}</span>
                </div>
                <div class="card-detail">${retText}</div>
                <span class="source-tag">${fData.source}</span>
              </div>
            `;
          }).join('');
        } else {
          fRetCont.innerHTML = `<p>${fData.detail || 'No return flights found.'}</p>`;
        }
      } else {
        fRetSec.classList.add('hidden');
      }

      // Render Hotels
      const hCont = document.getElementById('hotelResults');
      document.getElementById('hotel-results-container').classList.remove('hidden');
      if (hRes.ok && hData.hotels && hData.hotels.length > 0) {
        hCont.innerHTML = hData.hotels.map((h, i) => `
          <div class="option-card" id="hotel-opt-${i}" onclick="app.selectHotel(${i}, ${parseFloat(h.total_price)}, '${h.hotel_name.replace(/'/g,"")}', '${h.currency || ''}', '${(h.address || '').replace(/'/g,"")}', '${h.offer_id || h.hotel_id}')">
            <div class="card-header">
              <h3 class="card-title">${h.hotel_name}</h3>
              <span class="card-price">$${h.total_price}</span>
            </div>
            <div class="card-detail">${h.room_name || 'Standard Room'}</div>
            <div class="card-detail">${h.address || ''}</div>
            <span class="source-tag">${hData.source}</span>
          </div>
        `).join('');
      } else {
        hCont.innerHTML = `<p>${hData.detail || 'No hotels found.'}</p>`;
      }

    } catch (e) {
      document.getElementById('search-loading').classList.add('hidden');
      alert("Error fetching options: " + e.message);
    }
  },

  selectFlight(type, index, price, name, currency, offerId) {
    if (type === 'out') {
      document.querySelectorAll('#flightResults .option-card').forEach(c => c.classList.remove('selected'));
      document.getElementById(`flight-out-opt-${index}`).classList.add('selected');
      this.selectedOutboundFlight = { price, name, currency, offerId };
    } else {
      document.querySelectorAll('#returnFlightResults .option-card').forEach(c => c.classList.remove('selected'));
      document.getElementById(`flight-ret-opt-${index}`).classList.add('selected');
      this.selectedReturnFlight = { price, name, currency, offerId };
    }
    this.updateSummary();
  },

  selectHotel(index, price, name, currency, address, offerId) {
    document.querySelectorAll('#hotelResults .option-card').forEach(c => c.classList.remove('selected'));
    document.getElementById(`hotel-opt-${index}`).classList.add('selected');
    this.selectedHotel = { price, name, currency, offerId };
    this.updateSummary();
    
    // Update logistics based on selection
    const distEl = document.getElementById('context-distances');
    if (distEl && this.clientAddress) {
      let mins = 10 + (index * 4);
      let desc = "taxi";
      
      const clientStr = (this.clientAddress || "").toLowerCase();
      const hotelStr = (name || "").toLowerCase() + " " + (address || "").toLowerCase();
      
      // More forgiving match: just find the first word that is at least 4 letters (e.g. "collins")
      const match = clientStr.match(/[a-z]{4,}/i);
      if (match) {
        const keyword = match[0];
        if (hotelStr.includes(keyword)) {
          mins = 2 + (index % 3);
          desc = "walk";
        }
      }
      
      // Update Map to show the destination pin
      const mapFrame = document.getElementById('context-map');
      if (mapFrame) {
        mapFrame.src = `https://maps.google.com/maps?q=${encodeURIComponent(name + ' ' + address)}&output=embed`;
      }

      // Generate the official Google Maps directions URL
      const destCity = document.getElementById('destination').value || '';
      const originQuery = encodeURIComponent(`${name}, ${address || ''}`);
      const destQuery = encodeURIComponent(`${this.clientAddress}, ${destCity}`);
      const mapsUrl = `https://www.google.com/maps/dir/?api=1&origin=${originQuery}&destination=${destQuery}`;

      distEl.innerHTML = `
        Estimated travel time from Airport to ${this.clientAddress} is ~45 mins. <br/>
        <strong><span style="color:var(--accent);">✓ ${name}</span> is ~${mins} mins (${desc}) to ${this.clientAddress}.</strong>
        <div style="margin-top: 8px;">
          <a href="${mapsUrl}" target="_blank" style="display: inline-flex; align-items: center; gap: 4px; background: var(--accent); color: white; padding: 4px 10px; border-radius: 4px; text-decoration: none; font-weight: 500;">
            <svg width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7"></path></svg>
            Open Route in Google Maps
          </a>
        </div>
      `;
    }
  },

  updateSummary() {
    const fOutCost = this.selectedOutboundFlight ? this.selectedOutboundFlight.price : 0;
    const fRetCost = this.selectedReturnFlight ? this.selectedReturnFlight.price : 0;
    const hCost = this.selectedHotel ? this.selectedHotel.price : 0;
    const total = fOutCost + fRetCost + hCost;

    let flightName = 'None selected';
    let flightCostText = '$0';
    if (this.selectedOutboundFlight && this.selectedReturnFlight) {
        flightName = `Out: ${this.selectedOutboundFlight.name} / Ret: ${this.selectedReturnFlight.name}`;
        flightCostText = `$${(fOutCost + fRetCost).toFixed(2)}`;
    } else if (this.selectedOutboundFlight) {
        flightName = `${this.selectedOutboundFlight.name} (One-Way)`;
        flightCostText = `$${fOutCost.toFixed(2)}`;
    } else if (this.selectedReturnFlight) {
        flightName = `${this.selectedReturnFlight.name} (Return Only)`;
        flightCostText = `$${fRetCost.toFixed(2)}`;
    }

    document.getElementById('summary-flight-details').textContent = flightName;
    document.getElementById('summary-flight-cost').textContent = flightCostText;

    document.getElementById('summary-hotel-details').textContent = this.selectedHotel ? this.selectedHotel.name : 'None selected';
    document.getElementById('summary-hotel-cost').textContent = this.selectedHotel ? `$${hCost.toFixed(2)}` : '$0';

    document.getElementById('summary-total-cost').textContent = `$${total.toFixed(2)}`;
  },

  async bookItinerary() {
    if (!this.selectedOutboundFlight && !this.selectedHotel) {
      alert("Please select at least a flight or a hotel.");
      return;
    }

    const modal = document.getElementById('booking-modal');
    const statusDiv = document.getElementById('booking-status');
    const closeBtn = document.getElementById('booking-close-btn');
    
    modal.classList.remove('hidden');
    closeBtn.classList.add('hidden');
    statusDiv.innerHTML = "Initializing booking process...<br/>";
    
    // Helper to log to modal
    const log = (msg) => { statusDiv.innerHTML += msg + "<br/>"; };

    // Get Mock User Data
    let profile = this.currentProfile;
    if (!profile) {
      profile = { name: "Jane Ngo", email: "jane@example.com", phone: "+1234567890" };
    }
    const names = profile.name.split(" ");
    const given_name = names[0];
    const family_name = names.length > 1 ? names.slice(1).join(" ") : "Smith";

    try {
      let bookedItems = [];

      // 1. Book Outbound Flight
      if (this.selectedOutboundFlight && this.selectedOutboundFlight.offerId) {
        log("✈️ Booking Outbound Flight with Duffel Sandbox...");
        const res = await fetch('/flights/book', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'x-api-key': this.apiKey },
          body: JSON.stringify({
            offer_id: this.selectedOutboundFlight.offerId,
            given_name, family_name, born_on: "1980-01-01", gender: "f",
            email: profile.email || "jane@example.com", phone: profile.phone || "+442080162590",
            confirm: true
          })
        });
        const data = await res.json();
        if (res.ok && data.data && data.data.id) {
          const ref = data.data.booking_reference || data.data.id.substring(0,8);
          log(`✅ Outbound Flight Confirmed! PNR: <strong>${ref}</strong>`);
          bookedItems.push({
            type: "Flight (Outbound)",
            description: this.selectedOutboundFlight.name,
            amount: this.selectedOutboundFlight.price,
            reference: ref
          });
        } else {
          log(`❌ Outbound Flight Failed: ${data.detail || 'Unknown error'}`);
        }
      }

      // 2. Book Return Flight
      if (this.selectedReturnFlight && this.selectedReturnFlight.offerId) {
        log("✈️ Booking Return Flight with Duffel Sandbox...");
        const res = await fetch('/flights/book', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'x-api-key': this.apiKey },
          body: JSON.stringify({
            offer_id: this.selectedReturnFlight.offerId,
            given_name, family_name, born_on: "1980-01-01", gender: "f",
            email: profile.email || "jane@example.com", phone: profile.phone || "+442080162590",
            confirm: true
          })
        });
        const data = await res.json();
        if (res.ok && data.data && data.data.id) {
          const ref = data.data.booking_reference || data.data.id.substring(0,8);
          log(`✅ Return Flight Confirmed! PNR: <strong>${ref}</strong>`);
          bookedItems.push({
            type: "Flight (Return)",
            description: this.selectedReturnFlight.name,
            amount: this.selectedReturnFlight.price,
            reference: ref
          });
        } else {
          log(`❌ Return Flight Failed: ${data.detail || 'Unknown error'}`);
        }
      }

      // 3. Pre-Book Hotel
      if (this.selectedHotel && this.selectedHotel.offerId && this.selectedHotel.offerId !== 'undefined') {
        log("🏨 Pre-booking Hotel with LiteAPI Sandbox...");
        const res = await fetch(`/hotels/prebook?offer_id=${this.selectedHotel.offerId}`, {
          method: 'POST',
          headers: { 'x-api-key': this.apiKey }
        });
        const data = await res.json();
        if (res.ok && data.prebook_id) {
          log(`✅ Hotel Pre-booked! Ref: <strong>${data.prebook_id}</strong>`);
          bookedItems.push({
            type: "Hotel",
            description: this.selectedHotel.name,
            amount: this.selectedHotel.price,
            reference: data.prebook_id
          });
        } else {
          log(`❌ Hotel Pre-book Failed: ${data.detail || 'Offer expired or invalid'}`);
        }
      }

      log("<br/><strong style='color:var(--primary);'>🎉 Itinerary successfully booked in Sandbox environments!</strong>");
      
      // Save Trip
      if (bookedItems.length > 0) {
        log("<br/><span style='color:var(--text-muted)'>Saving trip receipt...</span>");
        await fetch('/trips', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'x-api-key': this.apiKey },
          body: JSON.stringify({
            traveler: profile.name,
            items: bookedItems
          })
        });
        log("✅ Trip saved to history.");
      }

    } catch (e) {
      log(`<br/><span style="color:var(--warning)">Error connecting to endpoints: ${e.message}</span>`);
    } finally {
      closeBtn.classList.remove('hidden');
    }
  },

  addDays(dateString, days) {
    const d = new Date(dateString);
    d.setDate(d.getDate() + days);
    return d.toISOString().split('T')[0];
  },

  async loadHistory() {
    const list = document.getElementById('history-list');
    list.innerHTML = 'Loading...';
    try {
      const res = await fetch('/trips', { headers: { 'x-api-key': this.apiKey } });
      const trips = await res.json();
      if (trips.length === 0) {
        list.innerHTML = '<p>No past trips found.</p>';
        return;
      }
      
      list.innerHTML = trips.map(t => `
        <div class="receipt-card">
          <div class="receipt-header">
            <h3>Tax Invoice / Receipt</h3>
            <button class="secondary no-print" onclick="app.printReceipt(this)">Print to PDF (Xero)</button>
          </div>
          <div class="receipt-meta">
            <div><strong>Date:</strong> ${new Date(t.created_at).toLocaleDateString()}</div>
            <div><strong>Traveler:</strong> ${t.traveler}</div>
            <div><strong>Receipt ID:</strong> ${t.id}</div>
          </div>
          <table class="receipt-table">
            <thead>
              <tr>
                <th>Item</th>
                <th>Reference</th>
                <th style="text-align:right">Amount (AUD)</th>
              </tr>
            </thead>
            <tbody>
              ${t.items.map(item => `
                <tr>
                  <td>${item.type}<br/><small>${item.description}</small></td>
                  <td>${item.reference}</td>
                  <td style="text-align:right">$${parseFloat(item.amount).toFixed(2)}</td>
                </tr>
              `).join('')}
            </tbody>
          </table>
          <div class="receipt-summary">
            <div class="summary-line"><span>Base Amount:</span> <span>$${t.summary.base_amount.toFixed(2)}</span></div>
            <div class="summary-line"><span>Includes GST (10%):</span> <span>$${t.summary.gst_amount.toFixed(2)}</span></div>
            <div class="summary-line total"><span>Total Paid:</span> <span>$${t.summary.total_amount.toFixed(2)} ${t.summary.currency}</span></div>
          </div>
        </div>
      `).join('');
    } catch (e) {
      list.innerHTML = `<p style="color:var(--warning)">Error loading history: ${e.message}</p>`;
    }
  },

  printReceipt(btnElement) {
    // Hide all receipts except the one we want to print
    document.querySelectorAll('.receipt-card').forEach(c => c.classList.add('print-hidden'));
    btnElement.closest('.receipt-card').classList.remove('print-hidden');
    window.print();
    // Restore all
    document.querySelectorAll('.receipt-card').forEach(c => c.classList.remove('print-hidden'));
  }
};

app.init();
