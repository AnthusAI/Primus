'use client';

import { useEffect } from 'react';
import { useBrand } from '@/app/contexts/BrandContext';

interface BrandedTitleProps {
  pageTitle?: string;
}

/**
 * Client component that updates the document title based on brand configuration.
 * Falls back to "Primus" if no brand name is configured.
 * 
 * Uses a MutationObserver to watch for title changes and replace "Primus" with the brand name.
 */
export function BrandedTitle({ pageTitle }: BrandedTitleProps) {
  const { config } = useBrand();
  const brandName = config?.name || 'Primus';

  useEffect(() => {
    // If no custom brand is configured, don't do anything
    // Let Next.js handle the title normally
    if (!config?.name) {
      return;
    }

    const replacePrimusInTitle = () => {
      const currentTitle = document.title;
      
      if (pageTitle) {
        // If a specific page title is provided, use it
        const newTitle = `${pageTitle} - ${brandName}`;
        if (currentTitle === newTitle) {
          return;
        }
        document.title = newTitle;
      } else if (currentTitle && currentTitle.includes('Primus')) {
        // Replace "Primus" with the brand name in the existing title
        // This handles cases like "Tasks - Primus" or "Evaluations -- Primus"
        const brandedTitle = currentTitle.replace(/Primus/g, brandName);
        if (currentTitle === brandedTitle) {
          return;
        }
        document.title = brandedTitle;
      } else if (currentTitle && !currentTitle.includes(brandName)) {
        // If the title doesn't contain the brand name, append it
        // This handles cases like "AI Agent Incubator" -> "AI Agent Incubator - Acme"
        const brandedTitle = `${currentTitle} - ${brandName}`;
        if (currentTitle === brandedTitle) {
          return;
        }
        document.title = brandedTitle;
      }
    };

    // Initial replacement
    replacePrimusInTitle();

    // Also replace on multiple delays to catch any async title updates
    const timeoutId1 = setTimeout(replacePrimusInTitle, 100);
    const timeoutId2 = setTimeout(replacePrimusInTitle, 500);
    const timeoutId3 = setTimeout(replacePrimusInTitle, 1000);

    // Watch for title changes by observing the entire head element
    // This catches changes to the title element itself
    const observer = new MutationObserver((mutations) => {
      mutations.forEach((mutation) => {
        // Check if any of the mutations affected the title
        if (mutation.type === 'childList') {
          const titleChanged = Array.from(mutation.addedNodes).some(
            (node) => node.nodeName === 'TITLE'
          ) || Array.from(mutation.removedNodes).some(
            (node) => node.nodeName === 'TITLE'
          );
          
          if (titleChanged || mutation.target.nodeName === 'TITLE') {
            replacePrimusInTitle();
          }
        } else if (mutation.type === 'characterData' && mutation.target.parentNode?.nodeName === 'TITLE') {
          replacePrimusInTitle();
        }
      });
    });

    // Observe both the head and the title element
    const headElement = document.head;
    const titleElement = document.querySelector('title');
    
    if (headElement) {
      observer.observe(headElement, {
        childList: true,
        subtree: true,
        characterData: true,
      });
    }
    
    if (titleElement) {
      observer.observe(titleElement, {
        childList: true,
        characterData: true,
        subtree: true,
      });
    }

    // Cleanup
    return () => {
      clearTimeout(timeoutId1);
      clearTimeout(timeoutId2);
      clearTimeout(timeoutId3);
      observer.disconnect();
    };
  }, [pageTitle, brandName]);

  return null; // This component doesn't render anything
}

