export const cityCatalogPath = (citySlug: string): string => `/${citySlug}/catalog`

export const cityPlacePath = (citySlug: string, placeSlug: string): string => `/${citySlug}/places/${placeSlug}`

export const cityRouteBuildPath = (citySlug: string): string => `/${citySlug}/routes/build`

export const cityHomePath = (citySlug: string): string => `/${citySlug}`
