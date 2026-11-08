import React from 'react';

const shapes = {
    heart: (
        <path
            d="M12 20.4 4.2 13C.1 9.1 2.3 3.6 6.9 3.6c2.1 0 3.8 1.1 5.1 2.8 1.3-1.7 3-2.8 5.1-2.8 4.6 0 6.8 5.5 2.7 9.4L12 20.4Z"
            fill="currentColor"
        />
    ),
    sparkle: (
        <path
            d="M12 1.5c1 5.9 3.2 8.1 9 9-5.8 1-8 3.2-9 9-1-5.8-3.2-8-9-9 5.8-.9 8-3.1 9-9Z"
            fill="currentColor"
        />
    ),
    asterisk: (
        <path
            d="M12 2v20M2 12h20M4.9 4.9l14.2 14.2M19.1 4.9 4.9 19.1"
            fill="none"
            stroke="currentColor"
            strokeWidth="2.4"
            strokeLinecap="round"
        />
    ),
    wave: (
        <>
            <path
                d="M7.2 12.2 5.9 6.9a1.5 1.5 0 0 1 2.9-.8l.9 3.3-.6-5.7a1.4 1.4 0 0 1 2.9-.3l.6 5.3.3-5.2a1.4 1.4 0 0 1 2.8.2l-.2 5 .7-3.4a1.4 1.4 0 0 1 2.8.5l-.9 6.9c-.3 4.6-2.8 7.2-6.9 7.2-3.1 0-5-1.5-6.4-3.8l-1.3-2a1.6 1.6 0 0 1 2.6-1.8l1.1 1.5Z"
                fill="currentColor"
            />
            <path
                d="M3.8 5.4 2.5 3.9M20 5.2l1.5-1.3"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.7"
                strokeLinecap="round"
            />
        </>
    ),
    burst: (
        <path
            d="m12 1.5 1.8 4.4 4.4-2-1.4 4.6 4.8.5-3.7 3 3.7 3-4.8.5 1.4 4.6-4.4-2-1.8 4.4-1.8-4.4-4.4 2 1.4-4.6-4.8-.5 3.7-3-3.7-3 4.8-.5-1.4-4.6 4.4 2L12 1.5Z"
            fill="currentColor"
        />
    ),
    star: (
        <path
            d="m12 2 2.9 6 6.6.9-4.8 4.7 1.2 6.6-5.9-3.1-5.9 3.1 1.2-6.6-4.8-4.7L9.1 8 12 2Z"
            fill="currentColor"
        />
    ),
    'arrow-up-right': (
        <path
            d="M5 19 19 5M8 5h11v11"
            fill="none"
            stroke="currentColor"
            strokeWidth="2.3"
            strokeLinecap="round"
            strokeLinejoin="round"
        />
    ),
    'arrow-left': (
        <path
            d="M20 12H4m0 0 6-6m-6 6 6 6"
            fill="none"
            stroke="currentColor"
            strokeWidth="2.3"
            strokeLinecap="round"
            strokeLinejoin="round"
        />
    ),
    'arrow-up': (
        <path
            d="M12 20V4m0 0-6 6m6-6 6 6"
            fill="none"
            stroke="currentColor"
            strokeWidth="2.3"
            strokeLinecap="round"
            strokeLinejoin="round"
        />
    ),
    cross: (
        <path
            d="m6 6 12 12M18 6 6 18"
            fill="none"
            stroke="currentColor"
            strokeWidth="2.3"
            strokeLinecap="round"
        />
    ),
};

export type IconName = keyof typeof shapes;

export default function Icon({ name }: { name: IconName }) {
    return (
        <svg
            aria-hidden="true"
            focusable="false"
            viewBox="0 0 24 24"
            style={{
                display: 'inline-block',
                width: '1em',
                height: '1em',
                flexShrink: 0,
                verticalAlign: '-0.14em',
            }}
        >
            {shapes[name]}
        </svg>
    );
}
