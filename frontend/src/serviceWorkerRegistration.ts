const isLocalhost = Boolean(
  window.location.hostname === "localhost" ||
    window.location.hostname === "[::1]" ||
    window.location.hostname.match(
      /^127(?:\.(?:25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)){3}$/
    )
);

type ServiceWorkerConfig = {
  onSuccess?: (registration: ServiceWorkerRegistration) => void;
  onUpdate?: (registration: ServiceWorkerRegistration) => void;
};

export const register = (config?: ServiceWorkerConfig): void => {
  if (process.env.NODE_ENV !== "production" || !("serviceWorker" in navigator)) {
    return;
  }

  const publicUrl = new URL(process.env.PUBLIC_URL, window.location.href);
  if (publicUrl.origin !== window.location.origin) {
    return;
  }

  window.addEventListener("load", () => {
    const swUrl = `${process.env.PUBLIC_URL}/service-worker.js`;

    if (isLocalhost) {
      checkValidServiceWorker(swUrl, config);
      navigator.serviceWorker.ready.then(() => {
        // Service worker ready in local dev.
      });
    } else {
      registerValidSW(swUrl, config);
    }
  });
};

const registerValidSW = (
  swUrl: string,
  config?: ServiceWorkerConfig
): void => {
  navigator.serviceWorker
    .register(swUrl)
    .then((registration) => {
      registration.onupdatefound = () => {
        const installingWorker = registration.installing;
        if (!installingWorker) {
          return;
        }
        installingWorker.onstatechange = () => {
          if (installingWorker.state === "installed") {
            if (navigator.serviceWorker.controller) {
              if (config?.onUpdate) {
                config.onUpdate(registration);
              }
            } else if (config?.onSuccess) {
              config.onSuccess(registration);
            }
          }
        };
      };
    })
    .catch(() => {
      // Ignorer les erreurs de registration.
    });
};

const checkValidServiceWorker = (
  swUrl: string,
  config?: ServiceWorkerConfig
): void => {
  fetch(swUrl, { headers: { "Service-Worker": "script" } })
    .then((response) => {
      const contentType = response.headers.get("content-type");
      if (response.status === 404 || !contentType?.includes("javascript")) {
        navigator.serviceWorker.ready
          .then((registration) => {
            registration.unregister();
          })
          .then(() => {
            window.location.reload();
          });
      } else {
        registerValidSW(swUrl, config);
      }
    })
    .catch(() => {
      // Offline.
    });
};

export const unregister = (): void => {
  if ("serviceWorker" in navigator) {
    navigator.serviceWorker.ready
      .then((registration) => {
        registration.unregister();
      })
      .catch(() => {
        // Ignorer les erreurs.
      });
  }
};
