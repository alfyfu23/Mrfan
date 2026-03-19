type StaticImage = import("next/image").StaticImageData;

declare module "*.css";

declare module "*.png" {
    const value: StaticImage;
    export default value;
}

declare module "*.jpg" {
    const value: StaticImage;
    export default value;
}

declare module "*.jpeg" {
    const value: StaticImage;
    export default value;
}

declare module "*.gif" {
    const value: StaticImage;
    export default value;
}

declare module "*.webp" {
    const value: StaticImage;
    export default value;
}

declare module "*.svg" {
    const value: StaticImage;
    export default value;
}
