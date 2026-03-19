import {
    dirname
} from "path";
import {
    fileURLToPath
} from "url";
import {
    FlatCompat
} from "@eslint/eslintrc";

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

const compat = new FlatCompat({
    baseDirectory: __dirname,
});

const eslintConfig = [
    ...compat.extends("next/core-web-vitals", "next/typescript"),
    {
        ignores: [
            "node_modules/**",
            ".next/**",
            "out/**",
            "build/**",
            "next-env.d.ts",
            ".coverage/**"
        ],
    },
    {
        rules: {
            "no-extra-boolean-cast": "off",
            "no-case-declarations": "off",
            "no-cond-assign": "off",
            "no-control-regex": "off",
            "no-inner-declarations": "off",
            "no-unused-expressions": "off",
            "@typescript-eslint/ban-ts-comment": "off",
            "@typescript-eslint/class-literal-property-style": "off",
            "@typescript-eslint/consistent-indexed-object-style": "off",
            "@typescript-eslint/consistent-generic-constructors": "off",
            "@typescript-eslint/no-duplicate-enum-values": "off",
            "@typescript-eslint/no-empty-function": "off",
            "@typescript-eslint/no-namespace": "off",
            "@typescript-eslint/no-non-null-asserted-optional-chain": "off",
            "@typescript-eslint/no-var-requires": "off",
            "@typescript-eslint/no-empty-interface": "off",
            "@typescript-eslint/no-explicit-any": "off",
            "@typescript-eslint/no-empty-object-type": "off",
            "@typescript-eslint/no-require-imports": "off",
            "@typescript-eslint/no-unused-vars": [
                "warn",
                {
                    argsIgnorePattern: "^(_+$|_[^_])",
                    varsIgnorePattern: "^(_+$|_[^_])",
                },
            ],
            "@typescript-eslint/no-inferrable-types": "off",
            "@typescript-eslint/prefer-optional-chain": "off",
            "no-restricted-globals": "off",
            "regexp/no-super-linear-backtracking": "off",
            "@typescript-eslint/interface-name-prefix": "off",
            "@typescript-eslint/prefer-function-type": "off",
            "@typescript-eslint/unified-signatures": "off",
            "@typescript-eslint/no-unsafe-function-type": "off",
            "@typescript-eslint/no-wrapper-object-types": "off",
            "@typescript-eslint/no-unused-vars": "off",
            "no-var": "off",
            "no-restricted-globals": "off",
            "no-shadow-restricted-names": "off",
            "no-restricted-syntax": "off",
            "@typescript-eslint/array-type": "off",
            "@next/next/no-img-element": "off",
        },
    },
];

export default eslintConfig;