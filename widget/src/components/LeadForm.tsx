/** Optional pre-chat lead capture form. */

import { h } from "preact";
import { useState } from "preact/hooks";

interface Props {
    fields: string[];
    primaryColor: string;
    onSubmit: (data: Record<string, string>) => void;
}

export function LeadForm({ fields, primaryColor, onSubmit }: Props) {
    const [values, setValues] = useState<Record<string, string>>({});

    const handleSubmit = (e: Event) => {
        e.preventDefault();
        onSubmit(values);
    };

    return (
        <form
            onSubmit={handleSubmit}
            style={{
                padding: "20px 16px",
                display: "flex",
                flexDirection: "column",
                gap: "12px",
            }}
        >
            <p style={{ margin: 0, fontSize: "14px", color: "#666" }}>
                Please share your details to get started:
            </p>
            {fields.map((field) => (
                <input
                    key={field}
                    type={field === "email" ? "email" : "text"}
                    placeholder={field.charAt(0).toUpperCase() + field.slice(1)}
                    required={field === "email"}
                    value={values[field] || ""}
                    onInput={(e) =>
                        setValues({ ...values, [field]: (e.target as HTMLInputElement).value })
                    }
                    style={{
                        padding: "10px 12px",
                        borderRadius: "8px",
                        border: "1px solid #ddd",
                        fontSize: "14px",
                        outline: "none",
                        fontFamily: "inherit",
                    }}
                />
            ))}
            <button
                type="submit"
                style={{
                    padding: "10px",
                    borderRadius: "8px",
                    backgroundColor: primaryColor,
                    color: "#fff",
                    border: "none",
                    fontSize: "14px",
                    cursor: "pointer",
                    fontFamily: "inherit",
                }}
            >
                Start Chat
            </button>
        </form>
    );
}
