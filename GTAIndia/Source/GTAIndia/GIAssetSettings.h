#pragma once

#include "CoreMinimal.h"
#include "Engine/DeveloperSettings.h"
#include "GIAssetSettings.generated.h"

class USkeletalMesh;
class UAnimSequence;
class UStaticMesh;
class UMaterialInterface;
class USoundBase;
class USoundAttenuation;

/** Animation set for one skeleton. Any entry may be empty; the anim instance falls back gracefully. */
USTRUCT(BlueprintType)
struct FGIAnimSet
{
	GENERATED_BODY()

	UPROPERTY(EditAnywhere, Category = "Anim") TSoftObjectPtr<UAnimSequence> Idle;
	UPROPERTY(EditAnywhere, Category = "Anim") TSoftObjectPtr<UAnimSequence> Walk;
	UPROPERTY(EditAnywhere, Category = "Anim") TSoftObjectPtr<UAnimSequence> Run;
	UPROPERTY(EditAnywhere, Category = "Anim") TSoftObjectPtr<UAnimSequence> Jump;
	UPROPERTY(EditAnywhere, Category = "Anim") TSoftObjectPtr<UAnimSequence> Fall;
	UPROPERTY(EditAnywhere, Category = "Anim") TSoftObjectPtr<UAnimSequence> Land;
	UPROPERTY(EditAnywhere, Category = "Anim") TSoftObjectPtr<UAnimSequence> Swim;
	UPROPERTY(EditAnywhere, Category = "Anim") TSoftObjectPtr<UAnimSequence> Sit;
	UPROPERTY(EditAnywhere, Category = "Anim") TSoftObjectPtr<UAnimSequence> Death;
	UPROPERTY(EditAnywhere, Category = "Anim") TSoftObjectPtr<UAnimSequence> PickUp;
	UPROPERTY(EditAnywhere, Category = "Anim") TSoftObjectPtr<UAnimSequence> Tread;
	UPROPERTY(EditAnywhere, Category = "Anim") TSoftObjectPtr<UAnimSequence> SitTalk;

	/** Ground speed (cm/s) at which the walk / run clips play at rate 1. */
	UPROPERTY(EditAnywhere, Category = "Anim") float WalkSpeed = 150.f;
	UPROPERTY(EditAnywhere, Category = "Anim") float RunSpeed = 400.f;
	/** Normalised time of the left-foot plant in each cycle (keeps walk / run legs in phase). */
	UPROPERTY(EditAnywhere, Category = "Anim") float WalkPlantPhase = 0.f;
	UPROPERTY(EditAnywhere, Category = "Anim") float RunPlantPhase = 0.f;
};

/** One NPC look: a mesh plus optional override materials. */
USTRUCT(BlueprintType)
struct FGICharacterLook
{
	GENERATED_BODY()

	UPROPERTY(EditAnywhere, Category = "Look") TSoftObjectPtr<USkeletalMesh> Mesh;
	/** Material slots (by name) that get a random clothing colour tint (needs OutfitTint params). */
	UPROPERTY(EditAnywhere, Category = "Look") TArray<FName> TintSlots;
	/** Whole-material alternatives for slot 0 (e.g. recoloured saree textures). */
	UPROPERTY(EditAnywhere, Category = "Look") TArray<TSoftObjectPtr<UMaterialInterface>> MaterialVariants;
	/** Relative weight when picking random pedestrians. */
	UPROPERTY(EditAnywhere, Category = "Look") float Weight = 1.f;
	/** Women / men etc. purely informative. */
	UPROPERTY(EditAnywhere, Category = "Look") FName Tag;
};

/** One spoken crowd line (Hindi TTS clip + romanised subtitle). */
USTRUCT(BlueprintType)
struct FGIVoiceLine
{
	GENERATED_BODY()

	UPROPERTY(EditAnywhere, Category = "Voice") TSoftObjectPtr<USoundBase> Sound;
	/** ambient | bump | bike | swim */
	UPROPERTY(EditAnywhere, Category = "Voice") FName Category;
	/** male | female */
	UPROPERTY(EditAnywhere, Category = "Voice") FName Gender;
	UPROPERTY(EditAnywhere, Category = "Voice") FString Text;
};

/**
 * Every asset path the C++ gameplay needs lives here (Config/DefaultGame.ini) so that the import
 * pipeline (Python) can wire assets without recompiling.
 */
UCLASS(Config = Game, DefaultConfig, meta = (DisplayName = "GTA India Assets"))
class GTAINDIA_API UGIAssetSettings : public UDeveloperSettings
{
	GENERATED_BODY()

public:
	static const UGIAssetSettings& Get() { return *GetDefault<UGIAssetSettings>(); }

	UPROPERTY(Config, EditAnywhere, Category = "Player") TSoftObjectPtr<USkeletalMesh> PlayerMesh;
	UPROPERTY(Config, EditAnywhere, Category = "Player") TSoftObjectPtr<UStaticMesh> DeliveryBoxMesh;
	/** Bone the delivery box is attached to. */
	UPROPERTY(Config, EditAnywhere, Category = "Player") FName DeliveryBoxBone = TEXT("spine_03");
	UPROPERTY(Config, EditAnywhere, Category = "Player") FVector DeliveryBoxOffset = FVector(0, -22, 0);

	/** Shared anim set: every character mesh uses the same skeleton. */
	UPROPERTY(Config, EditAnywhere, Category = "Anim") FGIAnimSet Anims;

	UPROPERTY(Config, EditAnywhere, Category = "Crowd") TArray<FGICharacterLook> PedestrianLooks;
	UPROPERTY(Config, EditAnywhere, Category = "Crowd") TSoftObjectPtr<UStaticMesh> CowMesh;

	UPROPERTY(Config, EditAnywhere, Category = "Vehicles") TSoftObjectPtr<UStaticMesh> BikeMesh;
	/** Bike mesh yaw correction so that +X is forward. */
	UPROPERTY(Config, EditAnywhere, Category = "Vehicles") float BikeMeshYaw = 0.f;
	UPROPERTY(Config, EditAnywhere, Category = "Vehicles") FVector BikeMeshOffset = FVector::ZeroVector;
	UPROPERTY(Config, EditAnywhere, Category = "Vehicles") float BikeMeshScale = 1.f;
	UPROPERTY(Config, EditAnywhere, Category = "Vehicles") TArray<TSoftObjectPtr<UStaticMesh>> TrainCarMeshes;
	UPROPERTY(Config, EditAnywhere, Category = "Vehicles") TSoftObjectPtr<UStaticMesh> TrainEngineMesh;
	/** Train car mesh yaw correction so that the long axis is +X. */
	UPROPERTY(Config, EditAnywhere, Category = "Vehicles") float TrainMeshYaw = 0.f;
	UPROPERTY(Config, EditAnywhere, Category = "Vehicles") float TrainMeshScale = 1.f;

	UPROPERTY(Config, EditAnywhere, Category = "UI") TSoftObjectPtr<UMaterialInterface> MinimapMaterial;
	UPROPERTY(Config, EditAnywhere, Category = "World") TSoftObjectPtr<UMaterialInterface> WaterMaterial;
	/** Translucent murk drawn around the camera underwater. */
	UPROPERTY(Config, EditAnywhere, Category = "World") TSoftObjectPtr<UMaterialInterface> UnderwaterMaterial;

	/** Applies a random outfit colour / material variant from Look to a crowd mesh component. */
	static void ApplyLookVariety(class USkeletalMeshComponent* Comp, const FGICharacterLook& Look, FRandomStream& Rand);
	// Audio (procedurally synthesised placeholders, see tools/audio).
	UPROPERTY(Config, EditAnywhere, Category = "Audio") TSoftObjectPtr<USoundBase> AmbRiver;
	UPROPERTY(Config, EditAnywhere, Category = "Audio") TSoftObjectPtr<USoundBase> AmbCity;
	UPROPERTY(Config, EditAnywhere, Category = "Audio") TSoftObjectPtr<USoundBase> TempleBells;
	UPROPERTY(Config, EditAnywhere, Category = "Audio") TSoftObjectPtr<USoundBase> TrainHorn;
	UPROPERTY(Config, EditAnywhere, Category = "Audio") TSoftObjectPtr<USoundBase> TrainLoop;
	UPROPERTY(Config, EditAnywhere, Category = "Audio") TSoftObjectPtr<USoundBase> BikeEngine;
	UPROPERTY(Config, EditAnywhere, Category = "Audio") TSoftObjectPtr<USoundBase> BikeHorn;
	UPROPERTY(Config, EditAnywhere, Category = "Audio") TSoftObjectPtr<USoundBase> Splash;
	UPROPERTY(Config, EditAnywhere, Category = "Audio") TSoftObjectPtr<USoundBase> SwimStroke;
	UPROPERTY(Config, EditAnywhere, Category = "Audio") TSoftObjectPtr<USoundBase> Cash;

	UPROPERTY(Config, EditAnywhere, Category = "Audio") TArray<FGIVoiceLine> VoiceLines;

	/** Runtime-created distance attenuation (inner radius, falloff distance). */
	static USoundAttenuation* MakeAttenuation(UObject* Outer, float Inner, float Falloff);

	/** Attribution lines shown on the Credits page (CC-BY assets). */
	UPROPERTY(Config, EditAnywhere, Category = "UI") TArray<FString> Credits;
	/** Emissive translucent material for the mission checkpoint cylinder. */
	UPROPERTY(Config, EditAnywhere, Category = "UI") TSoftObjectPtr<UMaterialInterface> MarkerMaterial;
};
