---
title: Contact
permalink: /contact/
layout: page
excerpt: Contact page.
comments: false
---

<p style="text-align:center;opacity:0.85;">Use this form to send a message directly from the website.</p>

<form id="contact-form" action="https://formspree.io/f/REPLACE_WITH_YOUR_FORM_ID" method="POST" style="width:640px;margin:1.5rem auto 0;display:grid;gap:0.9rem;">
    <label for="contact-name">Name</label>
    <input id="contact-name" name="name" type="text" required style="width:100%;box-sizing:border-box;padding:0.65rem;border:1px solid #bbb;border-radius:6px;" />

    <label for="contact-email">Email</label>
    <input id="contact-email" name="email" type="email" required style="width:100%;box-sizing:border-box;padding:0.65rem;border:1px solid #bbb;border-radius:6px;" />

    <label for="contact-message">Message</label>
    <textarea id="contact-message" name="message" rows="7" required style="width:100%;box-sizing:border-box;resize:vertical;min-height:10rem;padding:0.65rem;border:1px solid #bbb;border-radius:6px;"></textarea>

    <input type="text" name="_gotcha" style="display:none" tabindex="-1" autocomplete="off" />
    <input type="hidden" name="_subject" value="New website contact message" />

    <button type="submit" style="padding:0.7rem 1rem;border:1px solid #111;border-radius:6px;background:#111;color:#fff;cursor:pointer;">Send</button>
</form>

<p id="contact-note" style="text-align:center;opacity:0.8;font-size:0.95rem;margin-top:0.9rem;"></p>

<script>
    (function () {
        var form = document.getElementById("contact-form");
        var note = document.getElementById("contact-note");
        var submitButton = form ? form.querySelector("button[type='submit']") : null;

        if (!form) return;

        form.addEventListener("submit", async function (event) {
            event.preventDefault();

            if (form.action.indexOf("REPLACE_WITH_YOUR_FORM_ID") !== -1) {
                note.textContent = "Please replace REPLACE_WITH_YOUR_FORM_ID in email.md with your real Formspree form id.";
                return;
            }

            if (submitButton) {
                submitButton.disabled = true;
                submitButton.textContent = "Sending...";
            }

            note.textContent = "";

            try {
                var response = await fetch(form.action, {
                    method: "POST",
                    body: new FormData(form),
                    headers: { "Accept": "application/json" }
                });

                if (response.ok) {
                    form.reset();
                    note.textContent = "Message sent successfully. Thank you.";
                } else {
                    note.textContent = "Unable to send the message right now. Please try again.";
                }
            } catch (error) {
                note.textContent = "Network error while sending the message. Please try again.";
            } finally {
                if (submitButton) {
                    submitButton.disabled = false;
                    submitButton.textContent = "Send";
                }
            }
        });
    })();
</script>

